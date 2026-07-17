# Contribuindo

Obrigado por considerar contribuir com o Soundbar Keeper.

## Como colaborar

1. Faça um fork do repositório.
2. Crie uma branch descritiva, por exemplo: `feat/gui-settings`.
3. Implemente a mudança com foco em simplicidade, legibilidade e estabilidade no Windows.
4. Atualize a documentação quando a alteração impactar uso, configuração ou arquitetura.
5. Abra um Pull Request explicando o problema resolvido, a abordagem escolhida e como testar.

## Diretrizes do projeto

- Prefira código pequeno, modular e com responsabilidade clara.
- Use type hints em APIs novas ou alteradas.
- Evite comentários redundantes.
- Registre logs úteis para depuração, sem poluir o fluxo normal.
- Preserve compatibilidade com Windows.

## Ambiente de desenvolvimento

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -e .
```

## Testes manuais recomendados

- Validar abertura do ícone na bandeja do sistema.
- Confirmar que o app identifica a saída padrão corretamente.
- Testar pausa e retomada.
- Trocar entre a soundbar configurada e outro dispositivo de áudio.
- Verificar criação do arquivo de configuração.
- Verificar criação e remoção da inicialização automática.

## Relato de bugs

Ao abrir uma issue, inclua:

- versão do Windows
- versão do Python
- modelo da soundbar
- nome exato do dispositivo exibido no Windows
- trechos relevantes do log
