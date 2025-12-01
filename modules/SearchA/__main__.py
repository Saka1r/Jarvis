def run(message):
    import requests
    from playsound import playsound

    url = "https://api.intelligence.io.solutions/api/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lciI6IjMxOTc3Y2IzLTI3MjUtNDAzYS04ODQzLTY5MDJhY2Y5ZDY5YiIsImV4cCI6NDkxMDc1NDY5NX0.bLqEJYQXkgVxYr0WAn93qmzlEuZmtzUCrgJjYJ58TKTIpDxvQucOl7EeYtGsNe4RR85esxonFR-Gv_ZAleKOGQ"
    }

    data = {
        "model": "deepseek-ai/DeepSeek-R1-0528",
        "messages": [
            {
                "role": "system",
                "content": "You Jarvis you were created by Svyatoslav"
            },
            {
                "role": "user",
                "content": message
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    data  = response.json()

    playsound('config_files/jarvis_speech/search_ok.wav')

    text = data['choices'][0]['message']['content']
    print(text.split('</think>')[1])

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
    text = text.split('</think>')[1]
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