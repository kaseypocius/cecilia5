"""Render and inspect spectral audio in temporary folders; retain JSON only."""
import argparse
import hashlib
import gc
import json
import os
from pathlib import Path
import sys
import threading
import tempfile
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from Resources.AudioFileIO import AudioReader, AudioWriter
from Resources.OfflineRender import OfflineRenderManager, RenderSettings, RenderJob, apply_sound_to_snapshot
from check_all_modules import snapshot


def fixtures(folder, rate=48000):
    import pyo
    folder.mkdir(parents=True, exist_ok=True)
    sources = []
    for filename, name in [('accord.aif', 'recorded_chord'), ('transparent.aif', 'recorded_texture')]:
        original = Path(pyo.SNDS_PATH)/filename
        with AudioReader(original) as reader:
            info = reader.info
            data = reader.read(info.frames).mean(axis=1)
        # Resample the bundled recording and repeat it to an eight-second source.
        resampled = np.interp(np.arange(round(len(data)*rate/info.sample_rate))*info.sample_rate/rate,
                              np.arange(len(data)), data)
        signal = np.resize(resampled, 8*rate)
        stereo = np.column_stack((signal, np.roll(signal, round(.003*rate))))
        stereo *= .7/max(float(np.abs(stereo).max()), 1e-12)
        path = folder/(name+'.wav')
        with AudioWriter(path, rate, 2, len(stereo), 0, 3) as writer:
            writer.write(stereo)
        sources.append(path)
    return sources


def metrics(path):
    with AudioReader(path) as reader:
        info = reader.info
        count = 0
        squares = np.zeros(info.channels)
        peaks = np.zeros(info.channels)
        for block in reader.blocks():
            assert np.isfinite(block).all(), 'NaN/Inf in '+str(path)
            peaks = np.maximum(peaks, np.max(np.abs(block), axis=0))
            squares += np.sum(block*block, axis=0)
            count += len(block)
    rms = np.sqrt(squares/max(1, count))
    return {'frames': info.frames, 'sample_rate': info.sample_rate, 'channels': info.channels,
            'peak': peaks.tolist(), 'rms': rms.tolist(),
            'audible': bool(np.all(peaks > 1e-4) and np.all(rms > 1e-5)),
            'rms_dbfs': (20*np.log10(np.maximum(rms, 1e-12))).tolist()}


def module_snapshot(module, sources, seconds=4, channels=2):
    snap = snapshot(module, sources[0])
    slots = list(snap['modules'][0]['settings']['userInputs'])
    if len(slots) > 1:
        snap = apply_sound_to_snapshot(snap, str(sources[1]), input_name=slots[1])
    snap['output'].update(totalTime=seconds, nchnls=channels, gainSlider=-6)
    return snap


def render(snap, folder, label, rate=48000, channels=2, mode='single', sampletype=3):
    folder.mkdir(parents=True, exist_ok=True)
    output = folder/(label+'.wav')
    taps = {m['id']: str(folder/(label+'_'+m['id']+'.wav')) for m in snap['modules']}
    job = RenderJob(label, label, str(output), snap, module_outputs=taps)
    done = threading.Event()
    results = []
    manager = OfflineRenderManager(RenderSettings(sr=rate, nchnls=channels, num_threads=2,
        accel_mode=mode, buffersize=256, samp_size=sampletype, global_fade=.005),
        on_complete=lambda result: (results.append(result), done.set()))
    manager.start([job])
    if not done.wait(90):
        manager.cancel()
        manager._thread.join(timeout=10)
        raise TimeoutError(label+' exceeded 90 seconds')
    manager._thread.join(timeout=5)
    assert results[0].completed == 1 and not results[0].failed, job.error
    files = {'master': str(output), **taps}
    measured = {name: metrics(path) for name, path in files.items()}
    expected = (round(snap['output']['totalTime']*rate), rate, channels)
    for row in measured.values():
        assert (row['frames'], row['sample_rate'], row['channels']) == expected, row
    return measured, files


def live_render(snap, folder, label, rate=48000, channels=2):
    """Use the real live graph/start path with device-free native processing."""
    from pyo import Server, Record
    from Resources.OfflineRender import _HeadlessRenderWorker
    from Resources.Session import ChainSession
    worker = _HeadlessRenderWorker(lambda event: None)
    lib, shell = worker.CeciliaLib, worker.srv_shell
    for key, value in {'sr': rate, 'nchnls': channels, 'bufferSize': '256',
        'totalTime': snap['output']['totalTime'], 'globalFade': .005,
        'startOffset': 0, 'toDac': True, 'showSpectrum': False}.items():
        lib.setVar(key, value)
    shell.server = Server(sr=rate, nchnls=channels, buffersize=256, duplex=0, audio='manual').boot()
    shell.server.verbosity = 0
    shell.server.globalseed = 1
    __import__('random').seed(1)
    np.random.seed(1)
    chain = ChainSession()
    for index, entry in enumerate(snap['modules']):
        instance = shell.compileModule(entry['module_path'], entry.get('builtin', False), entry['id'])
        worker._populate_module_state(instance, entry, snap['output']['totalTime'], index == 0, snap['output'])
        chain.modules.append(instance)
    chain.restore_routing(snap)
    lib.session = chain
    assert shell.loadChain(), worker._last_error
    shell.setAmp(snap['output']['gainSlider'])
    folder.mkdir(parents=True, exist_ok=True)
    output = folder/(label+'.wav')
    recorder = None
    try:
        shell.start(timer=False)
        # Server.start performs spectral analysis before the live callback loop.
        # Record exactly the ensuing performance, as delivered by the live graph.
        recorder = Record(shell.output*shell.amp, filename=str(output), chnls=channels,
                          fileformat=0, sampletype=3, buffering=1)
        expected_frames = round(snap['output']['totalTime']*rate)
        for _ in range((expected_frames+255)//256):
            shell.server.process()
    finally:
        if recorder is not None:
            recorder.stop()
        recorder = None
        shell.server.stop()
        shell.cleanup_module()
        gc.collect()
        shell.server.shutdown()
    # The callback loop processes complete buffers. Retain exactly the requested
    # capture interval when (for example) 44.1 kHz does not divide the buffer size.
    trimmed = None
    with AudioReader(output) as reader:
        if reader.info.frames > expected_frames:
            trimmed = output.with_suffix('.trim.wav')
            with AudioWriter(trimmed, rate, channels, expected_frames, 0, 3) as writer:
                for block in reader.blocks(0, expected_frames):
                    writer.write(block)
    if trimmed is not None:
        trimmed.replace(output)
    measured = metrics(output)
    assert (measured['frames'], measured['sample_rate'], measured['channels']) == (
        round(snap['output']['totalTime']*rate), rate, channels), measured
    return {'master': measured}, {'master': str(output)}


def load_samples(path):
    with AudioReader(path) as reader:
        return reader.read(reader.info.frames)


def full_audit(modules, sources, report, prefix, rates=None):
    rows = []
    cases = [('offline44', render, 44100, 2, 'single', 3),
             ('live44', live_render, 44100, 2, None, None),
             ('offline48', render, 48000, 2, 'single', 3),
             ('chunks48', render, 48000, 2, 'chunks', 3),
             ('live48', live_render, 48000, 2, None, None),
             ('offline96_8ch', render, 96000, 8, 'single', 3),
             ('live96_8ch', live_render, 96000, 8, None, None),
             ('pcm24', render, 48000, 2, 'single', 1),
             ('high96_50ch', render, 96000, 50, 'single', 3),
             ('high192_50ch', render, 192000, 50, 'single', 3)]
    if rates:
        cases = [case for case in cases if case[2] in rates]
    with tempfile.TemporaryDirectory(prefix='cecilia-spectral-extra-') as directory:
        work = Path(directory)
        wide_sources = []
        for index, source in enumerate(sources):
            data = load_samples(source)
            wide = np.column_stack([np.roll(data[:, channel % 2], channel*17) for channel in range(50)])
            path = work/f'wide_{index}.wav'
            with AudioWriter(path, 48000, 50, len(wide), 0, 3) as writer:
                writer.write(wide)
            wide_sources.append(path)
        del data, wide
        for module in modules:
            samples = {}
            for label, runner, rate, channels, mode, sampletype in cases:
                snap = module_snapshot(module, wide_sources if channels == 50 else sources, channels=channels)
                folder = work/label
                try:
                    kwargs = {'rate': rate, 'channels': channels}
                    if runner is render:
                        kwargs.update(mode=mode, sampletype=sampletype)
                    measured, files = runner(snap, folder, module.stem, **kwargs)
                    assert all(value['audible'] for value in measured.values()), 'silent or inaudible output channel'
                    data = load_samples(files['master']) if channels != 50 else None
                    key = {44100: 'offline44', 48000: 'offline48', 96000: 'offline96_8ch'}.get(rate)
                    reference = samples.get(key) if channels != 50 else None
                    error = None
                    if reference is not None:
                        skip = int(.15*rate) if label.startswith('live') else 0
                        region = slice(skip, -skip) if skip else slice(None)
                        error = float(np.max(np.abs(data[region]-reference[region])))
                        # Live recording uses a float32 gain signal, while the
                        # server file writer applies its master gain separately.
                        # Retain absolute replay tolerance; permit float32-relative
                        # rounding only for this independent live capture path.
                        relative = 2e-6 if label.startswith('live') else 0
                        assert np.allclose(data[region], reference[region], atol=2e-6, rtol=relative), f'{label} differs from reference: {error}'
                    if data is not None:
                        samples[label] = data
                    independent_decode = False
                    if label == 'pcm24':
                        with wave.open(files['master'], 'rb') as stream:
                            assert (stream.getnframes(), stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) == (192000, 48000, 2, 3)
                            assert len(stream.readframes(192000)) == 192000*2*3
                        independent_decode = True
                    row = {'module': module.name, 'case': label, 'status': 'pass',
                           'measurements': measured, 'reference_max_error': error,
                           'comparison_edge_exclusion_seconds': .15 if label.startswith('live') else 0,
                           'comparison_relative_tolerance': relative if reference is not None else None,
                           'independent_wave_decode': independent_decode,
                           'audio': None,
                           'audio_sha256': hashlib.sha256(Path(files['master']).read_bytes()).hexdigest()}
                    # Inspect and hash the audio before removing it. The enclosing
                    # temporary folder also cleans partial outputs on failure.
                    for name, path in files.items():
                        Path(path).unlink()
                except Exception as error:
                    row = {'module': module.name, 'case': label, 'status': 'fail', 'error': str(error)}
                rows.append(row)
                print(json.dumps(row), flush=True)
                (report/(prefix+'.json')).write_text(json.dumps(rows, indent=2)+'\n')
    return rows


def functional_audit(sources, report):
    """Check meaningful parameter responses, including intentional gate silence."""
    rows = []
    with tempfile.TemporaryDirectory(prefix='cecilia-spectral-functions-') as directory:
        folder = Path(directory)
        source = load_samples(sources[0])
        quiet = folder/'quiet.wav'
        with AudioWriter(quiet, 48000, 2, len(source), 0, 3) as writer:
            writer.write(source*.005)
        t = np.arange(8*48000)/48000
        tones = folder/'tones.wav'
        signal = .35*np.sin(2*np.pi*t[:, None]*np.array([440, 660]))
        with AudioWriter(tones, 48000, 2, len(signal), 0, 3) as writer:
            writer.write(signal)
        sweep = folder/'two_notes.wav'
        frequencies = np.where(t < 4, 440, 880)
        signal = np.repeat((.35*np.sin(2*np.pi*t*frequencies))[:, None], 2, axis=1)
        with AudioWriter(sweep, 48000, 2, len(signal), 0, 3) as writer:
            writer.write(signal)
        cases = []
        for name in ['SpectralGate', 'Vectral']:
            for threshold in [-30, -90]:
                cases.append((name, f'quiet_gate_{threshold}', [quiet, sources[1]],
                              {'gthresh': [threshold, 0, None, 1]}, threshold == -90))
        cases.append(('Transpose', 'octave_up', [tones, sources[1]],
                      {'transpo1': [1200, 0, None, 1], 'transpo2': [1200, 0, None, 1],
                       'mix': [1, 0, None, 1]}, True))
        cases.append(('SpectralWarper', 'position_traverses_input', [sweep, sources[1]], {}, True))
        cases.append(('BinWarper', 'double_speed_traverses_input', [sweep, sources[1]],
                      {'low': [2, 0, None, 1], 'high': [2, 0, None, 1]}, True))
        for name in ['CrossSynth', 'CrossSynth2', 'Morphing']:
            cases.append((name, 'auxiliary_input_changes_output', [sources[0], sources[0]], {}, True))
        for name, label, inputs, sliders, expected_audible in cases:
            module = ROOT/'Resources/modules/Spectral'/(name+'.c5')
            snap = module_snapshot(module, inputs)
            snap['modules'][0]['settings']['userSliders'].update(sliders)
            for engine, runner in [('offline', render), ('live', live_render)]:
                row = {'module': name+'.c5', 'case': label, 'engine': engine,
                       'expected_audible': expected_audible, 'parameters': sliders}
                try:
                    measured, files = runner(snap, folder, name+'_'+engine)
                    assert measured['master']['audible'] == expected_audible, measured
                    data = load_samples(files['master'])
                    row['measurements'] = measured
                    if label == 'octave_up':
                        frequencies = np.argmax(np.abs(np.fft.rfft(data[48000:96000], axis=0))[1:], axis=0)+1
                        assert np.all(np.abs(frequencies-np.array([880, 1320])) <= 3), frequencies
                        row['dominant_hz'] = frequencies.tolist()
                    elif 'traverses_input' in label:
                        measured_frequencies = []
                        for start in [48000, 144000]:
                            section = data[start:start+24000, 0]
                            hz = (np.argmax(np.abs(np.fft.rfft(section))[1:])+1)*2
                            measured_frequencies.append(int(hz))
                        assert np.all(np.abs(np.array(measured_frequencies)-[440, 880]) <= 4), measured_frequencies
                        row['early_late_dominant_hz'] = measured_frequencies
                    elif label == 'auxiliary_input_changes_output':
                        # Generate a distinct-second-recording reference in this
                        # run, independent of any earlier audit's saved files.
                        reference_snap = module_snapshot(module, sources)
                        _, reference_files = runner(reference_snap, folder, name+'_'+engine+'_reference')
                        reference = load_samples(reference_files['master'])
                        delta = float(np.sqrt(np.mean((reference[7200:-7200]-data[7200:-7200])**2)))
                        assert delta > 1e-5, 'Secondary input had no measurable effect'
                        row['changed_input_rms_difference'] = delta
                        for path in reference_files.values():
                            Path(path).unlink()
                    row['status'] = 'pass'
                    for path in files.values():
                        Path(path).unlink()
                except Exception as error:
                    row.update(status='fail', error=str(error))
                rows.append(row)
                print(json.dumps(row), flush=True)
                (report/'spectral_audio_functions.json').write_text(json.dumps(rows, indent=2)+'\n')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix')
    parser.add_argument('--module', action='append')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--functional', action='store_true')
    parser.add_argument('--rates', nargs='+', type=int)
    args = parser.parse_args()
    if args.prefix is None:
        args.prefix = 'spectral_audio_full' if args.full else 'spectral_audio_probe'
    report = ROOT/'tests/reports'
    report.mkdir(parents=True, exist_ok=True)
    modules = sorted((ROOT/'Resources/modules/Spectral').glob('*.c5'))
    if args.module:
        modules = [module for module in modules if module.stem in args.module]
    # Own all generated inputs, exports, captures and taps for the entire run.
    # Context exit removes them on success, exceptions and Ctrl+C.
    with tempfile.TemporaryDirectory(prefix='cecilia-spectral-audio-') as directory:
        audio = Path(directory)
        sources = fixtures(audio/'inputs')
        if args.full:
            rows = full_audit(modules, sources, report, args.prefix, args.rates)
            return int(any(row['status'] != 'pass' for row in rows))
        if args.functional:
            rows = functional_audit(sources, report)
            return int(any(row['status'] != 'pass' for row in rows))
        rows = []
        for module in modules:
            snap = module_snapshot(module, sources)
            try:
                runner = live_render if args.live else render
                measured, files = runner(snap, audio/'outputs', module.stem)
                row = {'module': module.name, 'status': 'audible' if measured['master']['audible'] else 'silent_or_quiet',
                       'measurements': measured,
                       'audio_sha256': {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                        for name, path in files.items()}}
            except Exception as error:
                row = {'module': module.name, 'status': 'error', 'error': str(error)}
            rows.append(row)
            print(json.dumps(row), flush=True)
            (report/(args.prefix+'.json')).write_text(json.dumps(rows, indent=2)+'\n')
        return int(any(row['status'] != 'audible' for row in rows))


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='cecilia-spectral-profile-') as profile:
        previous_home = os.environ.get('HOME')
        os.environ['HOME'] = profile
        try:
            result = main()
        finally:
            if previous_home is None:
                os.environ.pop('HOME', None)
            else:
                os.environ['HOME'] = previous_home
    raise SystemExit(result)
