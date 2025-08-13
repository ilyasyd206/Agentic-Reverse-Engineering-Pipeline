# Factory Method

**Popis:** Tvorivý vzor, ktorý definuje rozhranie na vytváranie objektov, ale necháva podtriedy rozhodnúť, ktorý konkrétny typ vytvoria.

**Keď použiť:**  
- Keď trieda nechce priamo špecifikovať konkrétny typ objektu, ktorý vytvára.  
- Keď chceme delegovať zodpovednosť za tvorbu podtriedam.

**PlantUML-šablóna:**
```plantuml
@startuml
interface IProduct

class ConcreteProductA implements IProduct
class ConcreteProductB implements IProduct

interface ICreator {
  +factoryMethod(): IProduct
}

class ConcreteCreatorA implements ICreator {
  +factoryMethod(): ConcreteProductA
}

class ConcreteCreatorB implements ICreator {
  +factoryMethod(): ConcreteProductB
}

ICreator <|.. ConcreteCreatorA
ICreator <|.. ConcreteCreatorB
IProduct <|.. ConcreteProductA
IProduct <|.. ConcreteProductB
@enduml