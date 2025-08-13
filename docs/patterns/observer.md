# Observer

**Popis:** Behaviorálny vzor, ktorý zavádza mechanizmus odberu – objekty („pozorovatelia“) sa prihlásia k inému objektu („vydavateľovi“) a sú informované o zmene jeho stavu.

**Keď použiť:**  
- Keď zmena stavu jedného objektu musí automaticky upozorniť viacero závislých objektov.  
- Keď chceme dosiahnuť voľné prepojenie medzi vydavateľom a pozorovateľmi.

**PlantUML-šablóna:**
```plantuml
@startuml
interface IObserver {
  +update()
}

interface ISubject {
  +attach(o: IObserver)
  +detach(o: IObserver)
  +notify()
}

class ConcreteSubject implements ISubject {
  -state
  +attach()
  +detach()
  +notify()
  +businessLogic()
}

class ConcreteObserverA implements IObserver {
  +update()
}

class ConcreteObserverB implements IObserver {
  +update()
}

ISubject <|.. ConcreteSubject
IObserver <|.. ConcreteObserverA
IObserver <|.. ConcreteObserverB
ConcreteSubject --> IObserver : notifies
@enduml