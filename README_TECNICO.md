# Philips TAB4000 KeepAlive V9

## Resumo

Esta V9 evolui a arquitetura da V8 sem voltar ao fluxo constante da V6. O stream `sounddevice` fica aberto em WASAPI shared mode quando a soundbar Philips/TAB4000 esta disponivel. O callback envia silencio digital e mistura apenas micropulsos estereo de 3 a 6 ms, gerados fora do callback com frequencia aleatoria entre 18,0 kHz e 19,2 kHz, janela Hann/Blackman e fase inicial aleatoria.

## Principais componentes

- `philips_tab4000_keepalive_v9.py`: aplicacao principal da V9.
- `PulsePlanner`: pre-calcula pulsos e mantem uma fila de eventos para o callback leve.
- `OutputAudioMonitor`: le o pico do endpoint de saida do Windows via Core Audio e pausa os pulsos quando ha audio real.
- `KeepAliveApp`: controla estados `WAITING_FOR_DEVICE`, `OPENING_STREAM`, `RUNNING`, `REAL_AUDIO_ACTIVE`, `RECOVERING` e `STOPPING`.
- `TrayController`: bandeja com status, dispositivo atual, abertura de logs, reinicio do audio e saida.

## Detalhes de audio

- API: `sounddevice` + WASAPI shared mode.
- Formato: `float32`, estereo.
- Amplitude inicial: aproximadamente `-72 dBFS`.
- Intervalo entre pulsos: aleatorio entre 3 e 5 segundos.
- Duracao do pulso: aleatoria entre 3 e 6 ms.
- Frequencia por pulso: aleatoria entre 18,0 kHz e 19,2 kHz, limitada pelo Nyquist do sample rate configurado.
- Envelope: `Blackman` por padrao, com suporte a `Hann`.
- O callback nao faz randomizacao nem sintese pesada; ele apenas mistura pulsos previamente gerados.

## Detecao de audio real

A V9 nao usa apenas processo em execucao como sinal. Ela monitora o endpoint de saida padrao do Windows por `IAudioMeterInformation` via `PyCAW`. Quando o pico passa do threshold configurado pelo tempo de `attack`, os pulsos param completamente. Eles so retornam apos silencio continuo pelo tempo de `release`, com histerese entre `activate_threshold` e `release_threshold`.

Uma pequena janela de medicao ao redor do proprio pulso e ignorada para reduzir falso positivo causado pela injecao ultracurta.

## Limites fisicos conhecidos

O firmware da Philips TAB4000 nao expoe ao Windows uma telemetria confiavel de "entrou em standby fisico". A V9 detecta apenas:

- presenca do endpoint de audio;
- atividade do stream;
- audio real no medidor do endpoint.

Ela nao pode afirmar de forma garantida se a soundbar esta fisicamente acordada em todos os instantes, e isso e registrado em log e documentacao.

## Configuracao

O `config.json` fica em `%LOCALAPPDATA%\PhilipsTAB4000KeepAliveV9`. Atualizacoes preservam chaves existentes e completam apenas chaves novas do schema.

## Empacotamento

- Python alvo: 3.11
- Ambiente local: `.venv`
- Executavel final: `PhilipsTAB4000KeepAliveV9.exe`
- Instalador final: `PhilipsTAB4000KeepAliveV9_Setup.exe`
- Build script: `build_v9.ps1`
- Script do Inno Setup: `PhilipsTAB4000KeepAliveV9.iss`
