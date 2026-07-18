# Changelog

Todas as mudancas relevantes deste projeto serao documentadas neste arquivo.

O formato segue a ideia de um changelog legivel para humanos, inspirado em Keep a Changelog.

## [0.6.0] - 2026-07-18

### Added
- Migracao da logica da V6 WASAPI compartilhada para a arquitetura modular do repositorio.
- Watchdog de callback para reabrir o stream quando outro app interromper o fluxo.
- Protecao contra multiplas instancias simultaneas via mutex do Windows.
- Migracao automatica da configuracao legada da pasta `SoundbarKeeperV6`.
- Opcao `--list-devices` para diagnostico do nome exato da soundbar.
- Suporte a manter o PC acordado enquanto o app estiver ativo.

### Changed
- Configuracao padrao atualizada para o perfil de audio da V6.
- Runtime movido para `LOCALAPPDATA` para ficar alinhado ao comportamento da V6.

## [0.1.0] - 2026-07-17

### Added
- Estrutura profissional de repositorio para publicacao no GitHub.
- Aplicacao modular em `src/soundbar_keeper`.
- Monitoramento do dispositivo de saida padrao do Windows.
- Reproducao de tom quase inaudivel para manter soundbars ativas.
- Icone na bandeja do sistema com acoes de pausa, configuracao e encerramento.
- Suporte a inicializacao automatica com o Windows.
- Sistema de configuracao em JSON e logs em arquivo.
- Documentacao inicial, arquitetura, scripts de instalacao e contribuicao.
