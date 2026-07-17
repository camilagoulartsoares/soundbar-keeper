# Soundbar Keeper

Utilitário para Windows que mantém soundbars Bluetooth ativas enviando um fluxo de áudio quase inaudível apenas quando o dispositivo configurado estiver selecionado como saída padrão do sistema.

![GIF de demonstração placeholder](assets/screenshots/demo-placeholder.gif)
![Captura da bandeja placeholder](assets/screenshots/tray-placeholder.png)

## Descrição do projeto

Muitas soundbars Bluetooth entram automaticamente em modo de espera quando passam algum tempo sem receber áudio. O Soundbar Keeper foi criado para evitar esse comportamento enviando um tom de alta frequência, praticamente inaudível, com volume extremamente baixo, somente quando a soundbar desejada estiver ativa no Windows.

## Problema que resolve

O projeto reduz a frustração causada por soundbars que desligam sozinhas entre notificações, pausas curtas ou momentos de silêncio. Em vez de manter áudio audível tocando continuamente, o aplicativo usa um sinal discreto para ajudar a preservar a conexão e manter o equipamento acordado.

## Como funciona

1. O app inicia em segundo plano.
2. Ele observa qual é a saída padrão de áudio do Windows.
3. Quando a saída corresponde à soundbar configurada, o app inicia um stream com um tom em torno de `17.5 kHz`.
4. Quando outro dispositivo é selecionado, o stream é pausado automaticamente.
5. Se a soundbar voltar a ser a saída padrão, o keep-alive é retomado.

## Tecnologias utilizadas

- Python
- NumPy
- SoundDevice
- PyStray
- Pillow

## Requisitos

- Windows 10 ou Windows 11
- Python 3.11 ou superior
- Uma soundbar Bluetooth cujo nome possa ser identificado pelo Windows

## Instalação

```powershell
git clone https://github.com/camilagoulartsoares/soundbar-keeper.git
cd soundbar-keeper
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## Execução

```powershell
python -m soundbar_keeper
```

Após iniciar, o aplicativo permanece em segundo plano e exibe um ícone na bandeja do sistema.

## Como configurar

Na primeira execução, o Soundbar Keeper cria automaticamente um arquivo JSON em:

```text
%APPDATA%\SoundbarKeeper\config.json
```

Exemplo de configuração:

```json
{
  "device_name_patterns": ["Philips TAB4000"],
  "tone_frequency_hz": 17500.0,
  "volume": 0.0005,
  "sample_rate_hz": 44100,
  "check_interval_seconds": 3.0,
  "auto_start_with_windows": true,
  "start_paused": false,
  "log_level": "INFO"
}
```

Campos importantes:

- `device_name_patterns`: lista de nomes ou trechos de nomes que identificam a soundbar.
- `tone_frequency_hz`: frequência do tom de keep-alive.
- `volume`: amplitude do tom. Valores muito baixos são recomendados.
- `check_interval_seconds`: intervalo entre verificações da saída padrão.
- `auto_start_with_windows`: controla a inicialização automática.

Você também pode abrir o arquivo de configuração diretamente pelo menu do ícone na bandeja.

## Como instalar automaticamente

Para instalar o pacote e registrar a inicialização com o Windows:

```powershell
installer\install.bat
```

O script:

- instala o projeto em modo editável
- registra o aplicativo na pasta Startup do Windows
- deixa o comando pronto para execução local

## Como remover

Para remover a inicialização automática e desinstalar o pacote:

```powershell
installer\uninstall.bat
```

## Logs

Os logs ficam em:

```text
%APPDATA%\SoundbarKeeper\logs\
```

## Estrutura do projeto

```text
soundbar-keeper/
├── assets/
├── docs/
├── installer/
├── src/
│   └── soundbar_keeper/
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── pyproject.toml
└── requirements.txt
```

## Limitações

- O projeto depende do nome do dispositivo informado pelo Windows e acessível ao Python.
- Nem toda soundbar responde da mesma forma a sinais de alta frequência em volume muito baixo.
- A detecção da troca de dispositivo padrão é feita por verificação periódica, não por evento nativo do Windows.
- O app foi pensado para Windows e não pretende suportar Linux ou macOS.

## Licença

Distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE).

## Contribuição

Contribuições são bem-vindas. Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para orientações de desenvolvimento e testes manuais recomendados.

## Roadmap

- Interface gráfica (GUI)
- Instalador (.exe)
- Atualizador automático
- Configuração de frequência
- Configuração de volume
- Seleção de dispositivo
- Múltiplas soundbars
- Estatísticas de funcionamento
