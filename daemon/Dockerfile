FROM python:3.11-slim

WORKDIR /app

COPY ducky_game_hub_gamepad_daemon.py .

RUN chmod +x ducky_game_hub_gamepad_daemon.py

CMD ["python", "-u", "ducky_game_hub_gamepad_daemon.py"]
