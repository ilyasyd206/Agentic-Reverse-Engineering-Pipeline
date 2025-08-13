# Singleton

**Popis:** Tvorivý vzor, ktorý zabezpečuje, že trieda má len jednu inštanciu, a poskytuje globálny prístupový bod k tejto inštancii.

**Keď použiť:**  
- Keď potrebujeme jedinečnú inštanciu (napr. loger, cache, konfigurácia).  
- Keď chceme kontrolovať životný cyklus jediného objektu.

**PlantUML-šablóna:**
```plantuml
@startuml
class Singleton {
  -instance: Singleton
  +getInstance(): Singleton
  +businessMethod()
}
Singleton --> Singleton : „instance“
@enduml
