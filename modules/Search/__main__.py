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
