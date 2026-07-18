# Soundbar Keeper V8 UltraBurst

## O que e este projeto

O Soundbar Keeper V8 UltraBurst e um utilitario para Windows feito para tentar manter uma soundbar Bluetooth ativa por mais tempo, evitando que ela entre em modo de espera quando o sistema fica sem reproduzir audio audivel.

Esta versao foi pensada para trabalhar de forma discreta: em vez de enviar sinal constante ou pulsos fortes, ela injeta rajadas ultracurtas em frequencias muito altas para tentar manter o fluxo Bluetooth aberto com o minimo de percepcao sonora.

## O que foi feito nesta versao

Nesta V8, o projeto foi ajustado para usar uma estrategia mais leve do que as versoes anteriores:

- envia pulsos de aproximadamente 8 ms
- repete os pulsos a cada 20 segundos
- usa frequencias entre 19,2 kHz e 19,8 kHz
- aplica janela Blackman para suavizar as bordas do pulso e reduzir clique ou zumbido
- mantem o fluxo de audio aberto enquanto a soundbar compativel estiver selecionada
- monitora continuamente a saida de audio padrao do Windows
- grava configuracao e log em `%LOCALAPPDATA%\\SoundbarKeeperV8`
- oferece instalacao e desinstalacao por arquivos `.bat`

## O que ele faz

Quando o programa esta em execucao, ele:

1. verifica qual e a saida de audio padrao do Windows
2. confere se o dispositivo corresponde aos nomes configurados, como `Philips` ou `TAB4000`
3. abre um fluxo de audio para esse dispositivo
4. gera micropulsos quase imperceptiveis em intervalos definidos
5. tenta impedir que a soundbar desligue por inatividade
6. pode manter o Windows acordado enquanto estiver ativo

## Arquivos principais

- `soundbar_keeper_v8.py`: aplicacao principal da V8 UltraBurst
- `instalar_v8_ultraburst.bat`: script de instalacao
- `desinstalar_v8_ultraburst.bat`: script de remocao
- `LEIA-ME-PRIMEIRO.txt`: orientacoes rapidas de uso e teste

## Configuracao

Na primeira execucao, o programa cria um `config.json` em `%LOCALAPPDATA%\\SoundbarKeeperV8` com opcoes como:

- palavras-chave do dispositivo de audio
- taxa de amostragem
- intervalo entre pulsos
- duracao do pulso
- frequencias utilizadas
- amplitude do sinal
- modo de pulso duplo

Esses parametros existem para permitir testes mais conservadores ou mais agressivos, dependendo do comportamento da soundbar.

## Importante

O objetivo do projeto e tentar manter a soundbar ligada com o menor sinal possivel, mas nao existe garantia de funcionamento em todo aparelho. Filtros do Bluetooth, do driver de audio ou da propria soundbar podem impedir que as rajadas sejam reconhecidas como atividade.

Por isso, o ideal e fazer testes curtos antes de depender da ferramenta por longos periodos.
