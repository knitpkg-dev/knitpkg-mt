Vamos agora criar um novo Indicator como exemplo de criar um novo projeto. Criar um novo projeto é muito semelhante a criar um package. Mas este user guide não seria completo sem uma seção dedicada à criação de um projeto.

Vamos usar a função ATR de `calc` para criar um novo indicador. O projeto se chamará `atr` (binário KnitPkgATR.ex5).

Você pode seguir os passos 1-4 em [Creating Packages](creating-packages.md). No passo 2, execute `kp init` em MQL5/Indicators e selecione "indicator" no tipo de projeto.

Nota: estamos criando um indicador como exemplo de projeto para usar a função ATR de calc, mas eu poderia tranquilamente criar um Expert Advisor ou qualquer outro tipo de projeto para usar esta função.

Eu criei este repositório: https://forge.mql5.io/DouglasRechia/atr.git

E depois `kp init` usando include mode:

![alt text](images/terminal-init-atr.png)

Vamos agora adicionar e instalar as dependências:

```bash
kp add @douglasrechia/bar
kp add @douglasrechia/calc
kp install
```

Nota: Em um package, utiliza-se o `kp autocomplete`. Em outros tipos de projeto, utiliza-se o `kp install`.

Agora a entrada `dependencies` do manifest ficou assim:

```yaml
  '@douglasrechia/bar': ^1.1.0
  '@douglasrechia/calc': ^1.0.1
```

E o lock.json foi criado apontando para as respectivas versões resolvidas.

Vamos agora usar a função ATR de `calc` para criar um indicador ATR. O código final do indicador está [aqui](resources/KnitPkgATR.mq5).

Vamos compilar o indicador:

```bash
kp compile
```

E anexar a um gráfico para ver o resultado:

![alt text](images/metatrader-atr-indicator.png)

Agora, siga [Registering a New Project](registry.md/#registering-a-new-project).

Tudo feito, tente `kp info mql5 @douglasrechia/atr`.