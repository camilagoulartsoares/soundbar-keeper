# Philips TAB4000 KeepAlive V9

KeepAlive para Windows desenvolvido para evitar que a soundbar Philips TAB4000 entre em modo de espera (standby) durante longos periodos de silencio, garantindo que o primeiro audio (como um alarme do BlueStacks) seja reproduzido imediatamente.

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
README_INSTALACAO.md
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

# Logs

Os logs ficam em:

```text
%LOCALAPPDATA%\PhilipsTAB4000KeepAliveV9\logs
```

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

- Executavel
- Instalador

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
