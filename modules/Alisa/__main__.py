def run():

    import random

    pod = ["Are you by any chance Wi-Fi? What I feel between us.","If I had 5 rubles for every time I saw someone as beautiful as you, I would have 5 rubles.","Your face looks familiar to me. Were we in the same class by any chance? I could swear there's chemistry between us."]

    random_number = random.randint(0, 2)

    import os
    import torch

    from openvoice import se_extractor
    from openvoice.api import BaseSpeakerTTS, ToneColorConverter

    ckpt_base = 'checkpoints/base_speakers/EN'
    ckpt_converter = 'checkpoints/converter'
    device="cuda:0" if torch.cuda.is_available() else "cpu"
    output_dir = 'outputs'

    base_speaker_tts = BaseSpeakerTTS(f'{ckpt_base}/config.json', device=device)
    base_speaker_tts.load_ckpt(f'{ckpt_base}/checkpoint.pth')

    tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=device)
    tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')

    os.makedirs(output_dir, exist_ok=True)

    source_se = torch.load(f'{ckpt_base}/en_default_se.pth').to(device)

    reference_speaker = 'resources/reference_jarvis_big.wav' # This is the voice you want to clone
    target_se, audio_name = se_extractor.get_se(reference_speaker, tone_color_converter, target_dir='processed', vad=True)

    save_path = f'{output_dir}/output_en.wav'

    # Run the base speaker tts
    text = pod[random_number]
    src_path = f'{output_dir}/tmp.wav'
    base_speaker_tts.tts(text, src_path, speaker='default', language='English', speed=1.0)

    # Run the tone color converter
    encode_message = "@MyShell"
    tone_color_converter.convert(
        audio_src_path=src_path, 
        src_se=source_se, 
        tgt_se=target_se, 
        output_path=save_path,
        message=encode_message)
    
    from playsound import playsound

    playsound(f'{output_dir}/output_en.wav')
