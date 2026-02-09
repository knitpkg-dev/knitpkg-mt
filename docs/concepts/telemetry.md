Agora crie o arquivo docs/concepts/telemetry.md. Você sempre deve escrever tudo em inglês. Neste documento você deve explicar a telemetria do knitpkg. Siga o estilo de escrita dos demais arquivos em docs/concepts/*.md e não esqueça de sempre renderizar o markup com texto plano e trocando ``` por '''. Abaixo estão as explicações necessárias para o conteúdo que vc vai criar. Por favor, renderize em texto plano. Por favor, renderize em texto plano. 

A telemetria no knitpkg tem por objetivo coletar informações a respeito dos pacotes que são instalados pelo usuário. Nenhuma informação pessoal do usuário é coletada, e tudo o que é enviado ao registry relativo à telemetria é feito após autorização do usuário para tal.

A telemetria é utilizada para melhorar a experiência do usuário, permitindo que o knitpkg e o registry possam entender quais pacotes são mais utilizados, quais versões estão sendo mais adotadas, e quais dependências estão sendo mais comuns. Essas informações ajudam a equipe de desenvolvimento do knitpkg a priorizar melhorias, identificar possíveis problemas de compatibilidade, e otimizar o desempenho do sistema.

Além disso, com a informação de telemetria, será possível gerar futuramente o Health score que servirá como guia para os desenvolvedores escolherem quais organizações/desenvolvedores têm boa reputação suficiente para consumir/utilizar os seus pacotes.

A telemetria pode ser habilitada por projeto ou globalmente. Para saber mais como autorizar o envio da telemetria, ver [a referencia CLI](reference/cli.md).