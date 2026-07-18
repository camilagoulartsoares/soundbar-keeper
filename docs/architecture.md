# Arquitetura

O Soundbar Keeper foi organizado como um aplicativo Python modular orientado a responsabilidades bem definidas.

## Visao geral

O processo principal executa em segundo plano, observa a saida de audio padrao do Windows e liga ou desliga um fluxo de audio continuo em WASAPI compartilhado conforme a soundbar configurada esteja ativa.

## Fluxo principal

1. `main.py` inicializa logs, configuracao, auto start e loop de monitoramento.
2. `devices.py` consulta o dispositivo de saida padrao via `sounddevice`.
3. `audio.py` inicia ou interrompe um `OutputStream` com o perfil de audio herdado da V6.
4. `tray.py` expoe controles na bandeja do sistema.
5. `config.py` gerencia o arquivo JSON em `%LOCALAPPDATA%`.
6. `windows.py` cuida da integracao com o Windows, incluindo pasta de inicializacao, mutex de instancia unica e keep-awake.

## Modulos

- `audio.py`: geracao do sinal de keep-alive da V6, watchdog e controle do stream.
- `config.py`: dataclass da configuracao, leitura, escrita, recarga e migracao de config legada.
- `devices.py`: descoberta de dispositivos e logica de matching.
- `logger.py`: configuracao central de logging com arquivo rotativo.
- `main.py`: coordenacao da aplicacao.
- `resources.py`: caminhos de runtime, assets e diretorios de dados.
- `tray.py`: icone e menu de bandeja com PyStray.
- `windows.py`: abertura de arquivos, auto start, instancia unica e keep-awake.

## Decisoes importantes

- O monitoramento da saida padrao e feito por polling simples para reduzir dependencias externas.
- O perfil de audio da V6 usa multiplas frequencias baixas e volume extremamente baixo em WASAPI compartilhado.
- Um watchdog monitora a saude do callback para recuperar o stream quando outro software interfere.
- O auto start usa um script na pasta Startup do Windows para evitar dependencias adicionais.
- O arquivo de configuracao fica fora do diretorio do projeto para facilitar uso cotidiano.

## Limitacoes atuais

- O comportamento depende do nome do dispositivo exibido ao Python.
- Trocas de dispositivo sao detectadas por intervalo de verificacao, nao por evento nativo do Windows.
- Algumas soundbars podem exigir frequencias, taxa de amostragem ou volume diferentes.
