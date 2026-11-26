# PvM — publicação e configuração do Render

## Serviços do projeto

- **pvm-game**: site estático com o jogo (index.html).
- **pvm-admin-api**: API Python separada para autenticar o administrador e distribuir avisos, eventos e invocação do TAF aos jogadores online.

Os dois serviços usam o repositório MurylloRVK/pvm-game, branch main, com deploy automático.

## Configurar a senha do administrador (obrigatório)

A senha **não deve** ser colocada no index.html, em arquivos JavaScript, no GitHub, em render.yaml, nem enviada em mensagens.

1. Abra o serviço **pvm-admin-api** no Render.
2. Entre em **Environment**.
3. Em **Environment Variables**, clique em **Add**.
4. Crie a variável:
   - **Key:** PVM_ADMIN_PASSWORD
   - **Value:** uma senha nova, exclusiva e longa, que você não reutilize em outros lugares.
5. Salve usando **Save, rebuild, and deploy** (ou **Save and deploy**).

Depois que o serviço reiniciar, abra o PvM, entre no Painel de Administrador e use essa senha. Ela é enviada por HTTPS ao servidor para validação; o servidor não a devolve ao navegador. A sessão temporária fica apenas na memória da aba e termina ao sair/recarregar ou após expirar.

**Importante:** a senha que aparecia em versões antigas do JavaScript deve ser considerada comprometida. Não a reutilize.

## O que o painel global já distribui

- Comunicados/notificações para jogadores com o PvM aberto.
- Eventos e mutações de partida, com duração.
- Encerramento dos eventos globais.
- Invocação do TAF; se um jogador estiver no menu, o pedido fica aguardando a próxima fase por até 10 minutos.

A central não depende mais de uma aba de administrador hospedando uma conexão P2P. Os clientes consultam a API automaticamente.

## Limitações atuais do painel

- Contas, progresso, moedas e boosters ainda usam o armazenamento local de cada navegador.
- A lista de contas/boosters do painel é local ao navegador do administrador; ela ainda não administra perfis de outros jogadores.
- O relay entrega ações a quem está online naquele momento. Avisos não são uma caixa de entrada persistente para jogadores offline.
- A presença e a lista de eventos ficam em memória no serviço e são reiniciadas quando ele reinicia ou volta de suspensão.

O serviço pvm-admin-api usa o plano gratuito do Render. Serviços web gratuitos podem suspender após 15 minutos sem tráfego e precisam acordar quando chega uma nova solicitação; a primeira conexão depois disso pode demorar cerca de um minuto. Se jogadores estiverem com o PvM aberto, a consulta periódica mantém o serviço recebendo tráfego.

## Prévia de plantas

Antes de iniciar uma fase, a seleção de sementes mostra uma imagem estática da planta escolhida, desenhada pelo mesmo renderizador do Almanaque. A prévia usa um quadro congelado e não entra no ciclo de animação.

## Atualizar o jogo

Edite index.html, faça commit e envie para a branch main. Os serviços conectados recebem o deploy automaticamente.

## Contas e progresso

Contas, moedas, plantas personalizadas e progresso continuam guardados no localStorage do navegador. Cada navegador tem seu próprio armazenamento. Limpar os dados, mudar de domínio ou trocar de perfil pode fazer o progresso local parecer sumido. Faça backup/exportação dos dados quando disponível.

## Música do TAF

O HTML procura o arquivo The Aura Farmer - Horror Skunx (official song)_128k.mp3 ao lado do index.html. O áudio não está incluído no repositório. Só adicione áudio que você tenha autorização para hospedar e distribuir.
