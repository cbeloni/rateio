# Funcionalidades — Perfis e acesso de membros

> Registro da implementação do vínculo de usuários aos rateios e dos perfis por
> membro. A migração de banco foi criada, mas não foi executada neste ambiente.

## 1. Objetivo

Permitir que o mesmo usuário tenha papéis diferentes conforme o contexto:

- seja **organizador** dos rateios que criou;
- seja **membro** dos rateios em que foi cadastrado como membro;
- tenha acesso aos rateios participados após o cadastro e login;
- mantenha o perfil do vínculo editável na tela de membros.

O perfil global de `usuarios` não é alterado quando o usuário é associado a um
rateio. O perfil específico do vínculo fica em `membros.perfil`.

## 2. Vínculo por e-mail

O e-mail é a chave de associação entre `usuarios` e `membros`.

### Fluxo

1. O organizador cadastra um membro com e-mail.
2. O novo usuário realiza o cadastro público e confirma o e-mail.
3. No login, `service/auth_service.py` chama
   `repository.membro.vincular_por_email`.
4. A busca compara o e-mail sem diferenciar maiúsculas/minúsculas e ignorando
   espaços nas extremidades.
5. Todos os membros ativos com o e-mail correspondente recebem o
   `usuario_id` do usuário autenticado.
6. O usuário passa a visualizar todos os rateios dessas cotas.

Quando um membro é salvo com o e-mail de um usuário já existente, o vínculo
também é feito imediatamente em `api/rotas/gestao.py`.

## 3. Visibilidade e permissões

### Visualização

`_rateios_visiveis` e `service/dashboard.py` combinam:

- rateios cujo `organizador_id` é o usuário atual;
- rateios em que existe um membro ativo com o `usuario_id` do usuário atual.

Rateios duplicados são removidos pelo ID.

### Escrita

As rotas de alteração usam o dono do rateio como regra principal:

- `_rateio_acessivel`: permite leitura ao organizador ou a um membro ativo;
- `_rateio_do_organizador`: permite alteração somente ao usuário cujo ID é o
  `organizador_id` do rateio.

Assim, um membro pode visualizar o rateio, cotas, membros, categorias e
extrato, mas não pode alterar os dados do rateio.

As telas também ocultam controles de edição para quem não é o organizador do
rateio. A página de fechamentos trabalha somente com os rateios próprios.

## 4. Perfil por membro

O modelo `Membro` passou a possuir:

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `perfil` | `VARCHAR(20)` | `membro` | Perfil daquele vínculo dentro do rateio |

Perfis aceitos:

- `organizador`;
- `membro`.

### Regras de inicialização

- O cadastro público de usuário continua criando o usuário com perfil global
  `organizador`.
- Novos registros de membro começam com perfil `membro`.
- Se o organizador se cadastrar como membro da própria cota usando o próprio
  e-mail, o vínculo começa com perfil `organizador`.
- A migração inicializa como `organizador` os vínculos antigos cujo usuário é
  o organizador do rateio; os demais ficam como `membro`.

### Edição

Na tela de edição de uma cota, o organizador pode alterar o campo **Perfil** do
membro entre `Membro` e `Organizador`. O valor é validado no backend antes de
ser salvo.

O perfil é exibido na tabela de membros junto com nome, e-mail, telefone e
demais informações.

## 5. Arquivos envolvidos

| Arquivo | Alteração |
|---|---|
| `repository/membro.py` | Campo `perfil`, serialização e vínculo por e-mail |
| `service/auth_service.py` | Sincronização do vínculo durante o login |
| `api/rotas/gestao.py` | Regras de acesso, perfil padrão, edição e vínculo imediato |
| `service/dashboard.py` | Dashboard com rateios próprios e participados |
| `templates/rateios.html` | Diferenciação entre visualizar e editar |
| `templates/rateio.html` | Controles condicionados ao organizador do rateio |
| `templates/cota.html` | Exibição e edição do perfil do membro |
| `templates/categorias.html` | Edição disponível apenas ao organizador |
| `templates/extrato.html` | Atualização/classificação disponível apenas ao organizador |
| `migrations/versions/0008_membros_perfil.py` | Criação de `membros.perfil` e ajuste dos vínculos antigos |

## 6. Validação realizada

- `python -m compileall -q api service repository config dto util migrations/versions/0008_membros_perfil.py`
- `git diff --check`

Não foi iniciado o backend, não foi executada a migração e não foi feita
alteração direta no banco de dados.
