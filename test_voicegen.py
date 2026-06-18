from generators.voice_generator import generate_voice

script = {
    "hook": "Apple just made a surprising announcement.",

    "scenes": [
        {
            "text": "The company revealed a new AI feature for every iPhone."
        },
        {
            "text": "Investors reacted positively as shares climbed during trading."
        },
        {
            "text": "Experts believe this could reshape the smartphone market."
        }
    ],

    "cta": "Follow for daily tech updates."
}

generate_voice(script)