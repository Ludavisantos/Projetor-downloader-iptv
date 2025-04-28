# IPTV MP4 Downloader

Ferramenta CLI para baixar filmes de links IPTV (.m3u), alternando usuários/senhas automaticamente.

## Como usar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o programa:
   ```bash
   python downloader.py
   ```
3. Cadastre um ou mais usuários e senhas.
4. Escolha a opção para baixar filmes e informe o caminho do arquivo .m3u.

Os arquivos serão salvos na pasta `downloads` com o nome do título extraído do arquivo M3U.

## Observações
- O programa garante que cada par usuário/senha só será usado em um download por vez.
- Suporta múltiplos downloads simultâneos (um por usuário cadastrado).
