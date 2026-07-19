Philips TAB4000 KeepAlive V9

Arquivos esperados na raiz:
- PhilipsTAB4000KeepAliveV9_Setup.exe
- PhilipsTAB4000KeepAliveV9.exe
- README_TECNICO.md
- config.example.json

Instalacao:
1. Execute PhilipsTAB4000KeepAliveV9_Setup.exe.
2. O instalador copia a aplicacao para %LOCALAPPDATA%\PhilipsTAB4000KeepAliveV9.
3. A tarefa agendada PhilipsTAB4000KeepAliveV9 e recriada no logon com atraso de 10 segundos.
4. O app inicia sem console e fica na bandeja do Windows.

Logs:
- %LOCALAPPDATA%\PhilipsTAB4000KeepAliveV9\logs\keepalive.log

Limitacao fisica:
- O Windows nao informa com confianca quando a soundbar entrou fisicamente em standby.
- A V9 detecta apenas atividade de audio no endpoint de saida e o estado do stream WASAPI compartilhado.
