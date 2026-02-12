Vamos usar o novo projeto `barhelper` que criamos na seção anterior e as modificações em `expertdemo` para mostrar como registrar um novo package no registry e também como atualizar a versão de `expertdemo`.

## Como registrar um novo projeto

Para registrar um projeto no registry, precisamos seguir os seguintes passos:

1. Certifique-se de que o projeto esteja pronto para ser publicado. Isso inclui ter o manifest `knitpkg.yaml` corretamente configurado, com as dependências e a versão atualizada.

    - Aplicável somente para packages: Execute `kp checkinstall` para ter certeza que as diretivas @knitpkg:include estão corretas de forma que o KnitPkg poderá resolvê-las quando o package for instalado como dependência em outros projetos.

    - Adicione uma breve descrição desta revision/version no campo [`version_description`](../reference/manifest.md/#version_description-optional). Para novos projetos, geralmente utiliza-se 'Initial creation' ou coisa parecida.

    - Certifique-se de adicionar informações relevantes ao manifest para que seu projeto seja facilmente encontrado em uma busca no Registry. Mais sobre isso na sequência.

2. Faça o git commit e push para o repositório remoto. Certifique-se que o repositório remoto é **público**; se não for, configure-o para público.

3. Registre o projeto no registry com `kp register`.

## Como configurar o manifest para seu projeto ser encontrado facilmente no Registry

Para que seu projeto seja facilmente encontrado no Registry, é importante configurar o manifest `knitpkg.yaml` com as seguintes informações:

- [Description](../reference/manifest.md/#description-required): Descreva brevemente seu projeto: funcionalidades, dependências (se aplicáveis), etc.
- [Keywords](../reference/manifest.md/#keywords-optional): Adicione palavras-chave relevantes.

## Como funciona a busca no Registry

O Registry do KnitPkg permite que os usuários encontrem projetos por meio do comando [`kp search`](../reference/cli.md/#kp-search):

- Busca genérica - opção `--query`: esta opção busca os termos desejados pelos campos `name`, `keywords` e `description` dos manifests registrados no registry (nesta ordem de prioridade).
- Filtros - opções `--organization`, `--type`, `--author`, `--license`: filtra a busca pelos projetos que corresponderem aos termos exatos dos respectivos campos.
- Ordenação - opção `--sort-by` - use o nome de um dos campos do manifest para determinar qual deles será usado para ordenar a listagem.
- Ordenação - opção `--sort-order` - use `asc` para ordenação ascendente ou `desc` para descendente.
- Limitando o tamanho da busca por paginação - opções `--page` e `--page-size`: limite o número de projetos que serão retornados e especifique o número da página que será retornada caso necessário.

## Exemplo: Publicando o projeto `barhelper` no Git host

Vamos primeiro verificar o git status do projeto:

```bash
git status
```

O que deve produzir a seguinte saída:

```
On branch master

No commits yet

Untracked files:
  (use "git add <file>..." to include in what will be committed)
        .gitignore
        LICENSE
        README.md
        knitpkg.yaml
        knitpkg/
        tests/

nothing added to commit but untracked files present (use "git add" to track)
```

Nota: quando criamos o projeto `barhelper` com `kp init`, escolhemos inicializar o repositório git para o projeto, então o `git status` acima funcionará corretamente. Caso não tenha escolhido inicializar o repositório git, execute o comando `git init` *antes* de `git status` e você obterá a saída acima corretamente.

Vamos adicionar os arquivos ao stage e fazer o commit:

```bash
git add .
git commit -m 'Initial creation'
```

Agora precisamos criar a branch `main` (o default branch no MQL5Forge) e adicionar o repositório remoto para o projeto, para então fazer o push:

```bash
git switch -c main
git remote add origin https://forge.mql5.io/DouglasRechia/barhelper.git
git push -u origin main
```

Se necessário, altere a visibilidade de seu repositório para público. Repositórios privados não são permitidos na versão Free do KnitPkg. O projeto [`barhelper`](https://forge.mql5.io/DouglasRechia/barhelper.git) agora está no MQL5Forge!

## Registry login

Para fazer o registro, você precisa fazer login no Registry usando a sua conta/credenciais do Git host usando o comando [`kp login`](../reference/cli.md#kp-login), indicando qual o git provider:

```bash
kp login --provider mql5forge
```

O comando login abrirá o seu navegador para que você entre com suas credenciais do Git provider. A autenticação é segura via OAuth. O KnitPkg usará as suas credenciais para identificar quem você é e se está autorizado a publicar no Registry (mais sobre isso na sequência).

## Gerenciando o usuário conectado ao Registry

Você pode verificar o usuário conectado com [`kp whoami`](../reference/cli.md/#kp-whoami):

```
👤 User Information

  ID: 3
  Username: ---------
  Provider: mql5forge
  Email: -----@--------
  Subscription Tier: FREE
```

E pode deslogar do Registry com [`kp logout`](../reference/cli.md/#kp-logout).

## Registrando o projeto no Registry

 Para registrar o projeto, use [`kp register`](../reference/cli.md/#kp-register). Como exemplo, ver abaixo o comando para registrar o `barhelper`:

 ![alt text](images/vscode-project-register.png)

Ao registrar, o KnitPkg Registry confere se a visibilidade do repositório é público ou privado. Além disso, o Registry confirma se o usuário que publica tem permissão de escrita no repositório. Apenas usuários com permissão push no repositório podem registrar.

Nota: ao publicar, o usuário deve concordar com os [Terms of Service](../terms-of-service/registry.md).

Se quiser conferir o repositório publicado, tente [`kp info`](../reference/cli.md/#kp-info):

```bash
kp info mql5 @douglasrechia/barhelper
```

![alt text](images/vscode-kp-info-after-register.png)

## Buscando projetos no registry

O comando principal de busca é [`kp search`](../reference/cli.md/#kp-search). Abaixo um exemplo de busca pelo termo 'SMA':

```bash
kp search mql5 -q SMA
```

Tente a busca acima e explore algumas outras alternativas. Tente também outras [opções](../reference/cli.md/#kp-search).

Para informações detalhadas sobre as versões de um projeto, tente [`kp info`](../reference/cli.md/#kp-info)

## Version Yanking

Se você publicou uma versão de um projeto e depois percebeu que há um problema crítico nela, você pode usar o comando [`kp yank`](../reference/cli.md/#kp-yank) para marcar a versão como "yanked". Isso significa que a versão não será removida, mas não será mais resolvida com [version ranges](../reference/version-ranges.md/#yanked-versions). Mas uma versão yanked poderá ser resolvida com version spec exact match ou no modo --locked.

## Outros comandos relevantes para o Registry

Typically you interact with the registry through KnitPkg commands:

- `kp status` — Show registry status and configuration information
- `kp get` — Download and automatically build a project with a single command

See the [CLI reference](../reference/cli.md) and [Registry concepts](../concepts/registry.md) for more details.