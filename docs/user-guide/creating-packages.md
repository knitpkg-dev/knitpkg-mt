Vamos trabalhar no KnitPkg user guide. Agora você vai escrever o user-guide/creating-packages.md.

Você sempre deve escrever tudo em inglês. Siga o estilo de escrita dos arquivos em docs/concepts/*.md que você já conhece. 

Instruções para você me mandar conteúdo markdown: use ``` no início e ``` ao final para que o conteúdo seja renderizado para mim aqui no chat como texto plano; estes são os únicos lugares em que você pode usar ```. Se o markdown que você vai produzir precisar usar os limitadores ```, você vai escrever ''' ao invés de ```.

Abaixo eu vou colocar o que você precisa saber para escrever o user-guide/creating-packages.md

# Criando composite packages

Vamos criar um composite package chamado `barhelper` que fornece funções auxiliares para o pacote `bar`. Por exemplo, vamos implementar uma função `Cross` que retorna `true` ou `false` quando dois valores de `TimeSeries` se cruzam.

Dica: Recomendamos o [MetaEditor](https://www.metatrader5.com/en/automated-trading/metaeditor) para editar código fonte .mqh, .mq4 e .mq5. É uma IDE leve e segue o padrão recomendado MQL, além de possuir excelente IntelliSense. Para editar arquivos .yaml e outros, além de execução de comandos Git, recomendamos o [VSCode](https://code.visualstudio.com/), o qual pode ser configurado para syntax highlighting de código fonte MQL usando este [tutorial](https://www.mql5.com/en/blogs/post/719548).

Para criar um package, o primeiro passo é criar o repositório git. A seguir estão os links para os tutoriais de como fazer isso em cada um dos git hosts suportados: [MQL5Forge](https://forge.mql5.io/repo/create) (necessário [ativar a conta MQL5 storage](https://www.metatrader5.com/en/metaeditor/help/mql5storage/mql5storage_connect)), [GitHub](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository), [GitLab](https://docs.gitlab.com/user/project/) ou [Bitbucket](https://support.atlassian.com/bitbucket-cloud/docs/create-a-git-repository/).

Após criar o repositório, independente do provider, você terá uma Git URL como esta: [https://forge.mql5.io/DouglasRechia/barhelper.git](https://forge.mql5.io/DouglasRechia/barhelper.git). É importante entender o caminho Git do seu repositório: neste caso, ´DouglasRechia´ deve ser usado como organization do package após normalizado para letras minúsculas, e ´barhelper´ é o nome do repositório. O nome do repositório geralmente é o mesmo nome do projeto, mas isso não é obrigatório.

Nota: os git providers seguem este mesmo padrão para o path de um repositório git: 

- MQL5Forge: https://forge.mql5.io/organization/repository_name.git  
- GitHub: https://github.com/organization/repository_name.git
- GitLab: https://gitlab.com/organization/repository_name.git
- Bitbucket: https://bitbucket.org/organization/repository_name.git

Assim, já temos duas informações importantes para o manifest do novo package:

```yaml
organization: douglasrechia
name: barhelper
```

Para criar o package, vamos usar o comando `kp init`. O comando init fará uma série de perguntas para poder criar a estrutura do package para você:

