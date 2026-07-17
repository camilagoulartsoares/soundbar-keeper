# Arquitetura

O Soundbar Keeper foi organizado como um aplicativo Python modular orientado a responsabilidades bem definidas.

## Visão geral

O processo principal executa em segundo plano, observa a saída de áudio padrão do Windows e liga ou desliga um fluxo de áudio quase inaudível conforme a soundbar configurada esteja ativa.

## Fluxo principal

1. `main.py` inicializa logs, configuração, auto start e loop de monitoramento.
2. `devices.py` consulta o dispositivo de saída padrão via `sounddevice`.
3. `audio.py` inicia ou interrompe um `OutputStream` com um tom de alta frequência e volume mínimo.
4. `tray.py` expõe controles na bandeja do sistema.
5. `config.py` gerencia o arquivo JSON em `%APPDATA%`.
6. `windows.py` cuida da integração com o Windows, incluindo a pasta de inicialização.

## Módulos

- `audio.py`: geração do tom de keep-alive e controle do stream.
- `config.py`: dataclass da configuração, leitura, escrita e recarga.
- `devices.py`: descoberta de dispositivos e lógica de matching.
- `logger.py`: configuração central de logging com arquivo rotativo.
- `main.py`: coordenação da aplicação.
- `resources.py`: caminhos de runtime, assets e diretórios de dados.
- `tray.py`: ícone e menu de bandeja com PyStray.
- `windows.py`: abertura de arquivos/pastas e auto start.

## Decisões importantes

- O monitoramento da saída padrão é feito por polling simples para reduzir dependências externas.
- O tom de keep-alive usa frequência alta e amplitude muito baixa para minimizar impacto auditivo.
- O auto start usa um script na pasta Startup do Windows para evitar dependências adicionais.
- O arquivo de configuração fica fora do diretório do projeto para facilitar uso cotidiano.

## Limitações atuais

- O comportamento depende do nome do dispositivo exibido ao Python.
- Trocas de dispositivo são detectadas por intervalo de verificação, não por evento nativo do Windows.
- Algumas soundbars podem exigir frequência, taxa de amostragem ou volume diferentes.
