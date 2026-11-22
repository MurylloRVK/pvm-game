# PvM — publicação no Render

Este pacote é um site estático: o jogo roda no navegador e não precisa de servidor de aplicação para abrir.

## Arquivos

- `index.html`: jogo completo.
- `render.yaml`: configuração do Render Static Site.

## Publicar

1. Crie um repositório no GitHub chamado, por exemplo, `pvm-game`.
2. Envie `index.html` e `render.yaml` para a raiz do repositório (não coloque dentro de outra pasta).
3. No Render, escolha **New → Blueprint** e conecte o repositório. O `render.yaml` deste pacote configura o site estático automaticamente.
4. Revise o serviço `pvm-game` identificado no Blueprint e aplique a configuração.
5. Aguarde o primeiro deploy e abra a URL `*.onrender.com` para testar. Compartilhe essa URL com os amigos somente depois do teste.

Alternativa: em **New → Static Site**, conecte o mesmo repositório e configure Build Command como `echo "PvM estático - sem etapa de build"` e Publish Directory como `.`.

## Atualizar depois

Edite o `index.html`, salve, faça commit e envie (`push`) para a mesma branch do GitHub. Com o auto-deploy ligado, o Render publica a nova versão automaticamente.

## Contas e progresso — aviso importante

A versão atual guarda contas, moedas, plantas personalizadas e progresso em `localStorage` do navegador. Isso significa:

- Atualizar o mesmo site na mesma URL normalmente preserva os dados locais daquele navegador.
- Cada computador/navegador tem seu próprio armazenamento; as contas **não** são sincronizadas entre os amigos.
- Limpar os dados do navegador, mudar o domínio ou usar outro perfil pode fazer os dados locais parecerem sumidos.
- Antes de atualizar, faça backup/exportação do progresso no jogo, quando disponível.

Para contas compartilhadas e eventos globais para todos os jogadores, ainda será necessário um backend com autenticação e banco de dados. Este pacote não cria essa sincronização.

## Música do TAF

O HTML procura o arquivo `The Aura Farmer - Horror Skunx (official song)_128k.mp3` ao lado do `index.html`. O áudio não foi incluído neste pacote. Só adicione uma faixa ao repositório se você tiver autorização para hospedá-la e distribuí-la; caso contrário, mantenha a trilha alternativa do jogo ou use áudio próprio/licenciado.

## Teste antes de divulgar

- Abra o Adventure e selecione fases de regiões diferentes.
- Abra o Almanaque, lojas, laboratórios, Oficina do Caos e códigos.
- Crie uma planta no Laboratório e confira se aparece no seletor de sementes.
- Inicie uma partida de teste e invoque o TAF pelo painel de administrador.
- Confirme a barra de vida, música, zumbis de reforço e o estado de fúria abaixo de 10% de HP.
