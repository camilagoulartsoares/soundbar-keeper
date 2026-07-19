# Philips TAB4000 KeepAlive V9

KeepAlive para Windows desenvolvido para reduzir a chance de a soundbar Philips TAB4000 entrar em modo de espera (standby) durante longos periodos de silencio, ajudando a garantir que o primeiro audio, como um alarme do BlueStacks, seja reproduzido imediatamente.

---

# Objetivo

Algumas soundbars Bluetooth entram em standby apos alguns minutos sem audio.

Quando isso acontece, o primeiro som pode ser atrasado enquanto o dispositivo "acorda".

Este projeto mantem um stream WASAPI aberto e injeta micropulsos ultracurtos em intervalos aleatorios para reduzir a chance de a soundbar entrar em repouso.

---

# Principais recursos

- WASAPI Shared Mode
- Stream de audio sempre aberto
- Micropulsos ultracurtos (3-6 ms)
- Frequencia aleatoria entre 18,0 e 19,2 kHz
- Amplitude muito baixa (~ -72 dBFS)
- Janela Blackman/Hann
- Deteccao de audio real via PyCAW
- Pausa automatica dos pulsos durante reproducao de audio
- Recuperacao automatica do dispositivo Bluetooth
- Icone na bandeja do Windows
- Inicializacao automatica com o Windows
- Logs de diagnostico

---

# Estrutura do projeto

```text
philips_tab4000_keepalive_v9.py
build_v9.ps1
PhilipsTAB4000KeepAliveV9.spec
PhilipsTAB4000KeepAliveV9.iss
config.example.json
README.md
README_TECNICO.md
README_INSTALACAO.txt
requirements.txt
```

---

# Instalacao

## Usuario final

Baixe a versao mais recente em **Releases**.

Execute:

```text
PhilipsTAB4000KeepAliveV9_Setup.exe
```

Apos instalar:

1. Ligue a Philips TAB4000.
2. Conecte via Bluetooth.
3. O KeepAlive iniciara automaticamente com o Windows.

---

# Desenvolvimento

Esta secao explica como configurar um ambiente novo do zero em outro computador Windows.

## 1. Clonar o repositorio

```bash
git clone <URL_DO_REPOSITORIO>
cd <PASTA_DO_PROJETO>
```

## 2. Pre-requisitos

- Windows 10 ou superior
- Python 3.11
- Git
- Inno Setup (para gerar o instalador)
- PowerShell

## 3. Criar ambiente virtual

```bash
python -m venv .venv
```

## 4. Ativar o ambiente

Windows:

```powershell
.venv\Scripts\activate
```

## 5. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Executar em modo desenvolvimento

```bash
python philips_tab4000_keepalive_v9.py
```

## 7. Gerar o executavel e o instalador

```powershell
powershell -ExecutionPolicy Bypass -File build_v9.ps1
```

O script gera:

- `PhilipsTAB4000KeepAliveV9.exe`
- `PhilipsTAB4000KeepAliveV9_Setup.exe`

---

# Logs

Os logs ficam em:

```text
%LOCALAPPDATA%\PhilipsTAB4000KeepAliveV9\logs
```

---

# Configuracao

O arquivo `config.json` e criado automaticamente em:

```text
%LOCALAPPDATA%\PhilipsTAB4000KeepAliveV9
```

O arquivo `config.example.json` serve apenas como modelo de referencia para configuracoes.

---

# Compilacao

Pre-requisitos:

- Python 3.11
- Inno Setup
- Dependencias do `requirements.txt`

Depois execute:

```powershell
build_v9.ps1
```

O script gera:

- `PhilipsTAB4000KeepAliveV9.exe`
- `PhilipsTAB4000KeepAliveV9_Setup.exe`

---

# Atualizacoes

Para atualizar o projeto em uma maquina de desenvolvimento, basta fazer:

```bash
git pull
```

Depois execute novamente:

```powershell
build_v9.ps1
```

Isso gera uma nova versao do executavel e do instalador com base no estado atual do repositorio.

---

# Reproduzindo o ambiente

Qualquer desenvolvedor deve conseguir, apenas com o conteudo deste repositorio:

- clonar o repositorio;
- instalar as dependencias com `requirements.txt`;
- executar a aplicacao;
- gerar novamente o executavel;
- gerar novamente o instalador.

O projeto foi documentado para nao depender de arquivos exclusivos do computador original para build, execucao ou empacotamento.

---

# Limitacoes

O firmware da Philips TAB4000 nao informa ao Windows se entrou em standby fisico.

O software consegue detectar:

- dispositivo conectado;
- endpoint disponivel;
- atividade do stream;
- audio real.

Nao existe API publica que permita confirmar com 100% de certeza o estado fisico da soundbar.

---

# Status

Versao: **V9**

Testada em Windows com Philips TAB4000 via Bluetooth.

Teste pratico realizado:

- computador ligado durante toda a noite;
- soundbar conectada;
- nenhuma musica em reproducao;
- alarme do BlueStacks disparado pela manha;
- reproducao iniciada corretamente.

---

# Licenca

Uso pessoal e educacional.
