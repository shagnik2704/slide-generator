# Spoken Tutorial Knowledge Graph - Walkthrough

## Overview

This document outlines the architecture and implementation plan for building a **Knowledge Graph** from Spoken Tutorial's prerequisite data using **Neo4j**. The graph will enable automatic prerequisite detection, learning path generation, and content validation for the Slide Generator.

---

## What is a Knowledge Graph?

A knowledge graph represents knowledge as a network of interconnected entities and their relationships.

```mermaid
graph LR
    subgraph "Knowledge Graph Components"
        N[("🔵 Nodes<br/>(Entities)")]
        E[("🔗 Edges<br/>(Relationships)")]
        P[("📋 Properties<br/>(Attributes)")]
    end
    
    N --> E
    E --> P
```

In our context:
- **Nodes** = Tutorials, Topics, Concepts
- **Edges** = "requires", "teaches", "part_of"
- **Properties** = title, author, duration, level

---

## Python 3.4.3 Dependency Graph

Here's a sample dependency graph for the Python 3.4.3 series on Spoken Tutorial:

```mermaid
flowchart TD
    subgraph "Entry Point"
        LINUX["🐧 Linux Basics"]
    end
    
    subgraph "Level 1: Getting Started"
        IPYTHON["🚀 Getting Started<br/>with IPython"]
    end
    
    subgraph "Level 2: Core Concepts"
        DATATYPES["📊 Datatypes &<br/>Variables"]
        IO["📥 Input/Output"]
        PLOT["📈 Using Plot<br/>Interactively"]
    end
    
    subgraph "Level 3: Data Structures"
        STRINGS["📝 Strings"]
        OPERATORS["➕ Operators &<br/>Expressions"]
        LISTS1["📋 Lists Part 1"]
        LISTS2["📋 Lists Part 2"]
    end
    
    subgraph "Level 4: Control Flow"
        FORLOOP["🔄 For Loop"]
        WHILELOOP["🔁 While Loop"]
        CONDITIONAL["❓ Conditional<br/>Statements"]
        DICT["📖 Dictionaries"]
    end
    
    subgraph "Level 5: Functions & Modules"
        FUNCTIONS["⚡ Getting Started<br/>with Functions"]
        ADVANCED_FUNC["🔧 Advanced<br/>Functions"]
        FILES["📁 File Handling"]
        MODULES["📦 Modules"]
    end
    
    subgraph "Level 6: Advanced Topics"
        PANDAS["🐼 Data Analysis<br/>with Pandas"]
        SCRAPING["🕸️ Web Scraping"]
    end
    
    %% Relationships
    LINUX --> IPYTHON
    
    IPYTHON --> DATATYPES
    IPYTHON --> IO
    IPYTHON --> PLOT
    
    DATATYPES --> STRINGS
    DATATYPES --> OPERATORS
    
    STRINGS --> LISTS1
    LISTS1 --> LISTS2
    
    LISTS2 --> FORLOOP
    IO --> FORLOOP
    
    FORLOOP --> WHILELOOP
    FORLOOP --> CONDITIONAL
    FORLOOP --> DICT
    
    WHILELOOP --> FUNCTIONS
    CONDITIONAL --> FUNCTIONS
    
    FUNCTIONS --> ADVANCED_FUNC
    FUNCTIONS --> FILES
    FUNCTIONS --> MODULES
    
    FILES --> PANDAS
    PANDAS --> SCRAPING
    
    %% Styling
    classDef entry fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef level1 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef level2 fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef level3 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef level4 fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef level5 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef level6 fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    
    class LINUX entry
    class IPYTHON level1
    class DATATYPES,IO,PLOT level2
    class STRINGS,OPERATORS,LISTS1,LISTS2 level3
    class FORLOOP,WHILELOOP,CONDITIONAL,DICT level4
    class FUNCTIONS,ADVANCED_FUNC,FILES,MODULES level5
    class PANDAS,SCRAPING level6
```

---

## Cross-Topic Dependencies

Tutorials often have dependencies across different FOSS topics:

```mermaid
flowchart LR
    subgraph "Linux"
        L1["Terminal Basics"]
        L2["File Permissions"]
        L3["Text Editors"]
    end
    
    subgraph "Python"
        P1["Getting Started<br/>with IPython"]
        P2["File Handling"]
        P3["Web Scraping"]
    end
    
    subgraph "Scilab"
        S1["Getting Started<br/>with Scilab"]
        S2["Xcos Basics"]
    end
    
    subgraph "LaTeX"
        LT1["Getting Started<br/>with LaTeX"]
        LT2["Beamer<br/>Presentations"]
    end
    
    %% Cross-topic dependencies
    L1 --> P1
    L1 --> S1
    L1 --> LT1
    
    L2 --> P2
    L3 --> LT1
    
    P2 --> P3
    
    %% Styling
    classDef linux fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef python fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef scilab fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef latex fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    
    class L1,L2,L3 linux
    class P1,P2,P3 python
    class S1,S2 scilab
    class LT1,LT2 latex
```

---

## Data Flow Architecture

```mermaid
flowchart TB
    subgraph "Phase 1: Data Collection"
        ST["🌐 Spoken Tutorial<br/>Website"]
        SCRAPER["🕷️ Web Scraper<br/>(requests + BeautifulSoup)"]
        JSON["📄 Raw JSON Data"]
    end
    
    subgraph "Phase 2: Graph Construction"
        NEO4J[("🗄️ Neo4j<br/>Graph Database")]
        BUILDER["🔨 Graph Builder<br/>(py2neo)"]
    end
    
    subgraph "Phase 3: Query Layer"
        SERVICE["⚙️ Neo4j Service<br/>(Python)"]
        API["🔌 REST API<br/>(FastAPI)"]
    end
    
    subgraph "Phase 4: Integration"
        STRUCT["📐 structure_node.py"]
        EVAL["✅ evaluator_node.py"]
        FRONTEND["💻 React Frontend"]
    end
    
    ST --> SCRAPER
    SCRAPER --> JSON
    JSON --> BUILDER
    BUILDER --> NEO4J
    NEO4J --> SERVICE
    SERVICE --> API
    API --> STRUCT
    API --> EVAL
    API --> FRONTEND
    
    %% Styling
    classDef source fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef storage fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef integration fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    
    class ST,SCRAPER,JSON source
    class BUILDER,SERVICE,API process
    class NEO4J storage
    class STRUCT,EVAL,FRONTEND integration
```

---

## Neo4j Graph Schema

```mermaid
erDiagram
    TUTORIAL {
        string id PK
        string title
        string foss
        string level
        string language
        string author
        string duration
        string url
        string[] objectives
        string[] keywords
    }
    
    TOPIC {
        string id PK
        string name
        string description
        int tutorial_count
    }
    
    CONCEPT {
        string id PK
        string name
        string description
    }
    
    TUTORIAL ||--o{ TUTORIAL : "PREREQUISITE_FOR"
    TUTORIAL }o--|| TOPIC : "BELONGS_TO"
    TUTORIAL ||--o{ CONCEPT : "TEACHES"
    CONCEPT ||--o{ CONCEPT : "RELATED_TO"
```

---

## Example Queries

### Query 1: Get All Prerequisites (Recursive)

```mermaid
flowchart LR
    subgraph "Query: Prerequisites for Web Scraping"
        WS["🕸️ Web Scraping"]
        PD["🐼 Pandas"]
        FH["📁 File Handling"]
        FN["⚡ Functions"]
        FL["🔄 For Loop"]
        DT["📊 Datatypes"]
        IP["🚀 IPython"]
        LX["🐧 Linux"]
    end
    
    LX -->|"1"| IP
    IP -->|"2"| DT
    DT -->|"3"| FL
    FL -->|"4"| FN
    FN -->|"5"| FH
    FH -->|"6"| PD
    PD -->|"7"| WS
    
    style WS fill:#ff5722,stroke:#bf360c,stroke-width:3px,color:#fff
    style LX fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
```

**Result**: `[Linux, IPython, Datatypes, For Loop, Functions, File Handling, Pandas]`

---

### Query 2: What Can I Learn Next?

```mermaid
flowchart TB
    FL["🔄 For Loop<br/>(Completed)"]
    
    WL["🔁 While Loop"]
    CS["❓ Conditional<br/>Statements"]
    DI["📖 Dictionaries"]
    
    FL --> WL
    FL --> CS
    FL --> DI
    
    style FL fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    style WL fill:#2196f3,stroke:#0d47a1,stroke-width:2px,color:#fff
    style CS fill:#2196f3,stroke:#0d47a1,stroke-width:2px,color:#fff
    style DI fill:#2196f3,stroke:#0d47a1,stroke-width:2px,color:#fff
```

---

### Query 3: Shortest Learning Path

```mermaid
flowchart LR
    subgraph "Shortest Path: Beginner → Machine Learning"
        A["🐧 Linux<br/>Basics"] --> B["🚀 IPython"]
        B --> C["📊 Datatypes"]
        C --> D["📋 Lists"]
        D --> E["🔄 For Loop"]
        E --> F["⚡ Functions"]
        F --> G["📁 File<br/>Handling"]
        G --> H["🐼 Pandas"]
        H --> I["📈 NumPy"]
        I --> J["🤖 Machine<br/>Learning"]
    end
    
    style A fill:#4caf50,stroke:#1b5e20,stroke-width:2px,color:#fff
    style J fill:#ff5722,stroke:#bf360c,stroke-width:2px,color:#fff
```

---

## Integration with Slide Generator

### Use Case 1: Auto-populate Prerequisites Slide

```mermaid
sequenceDiagram
    participant User
    participant SlideGen as Slide Generator
    participant Neo4j as Neo4j Graph
    
    User->>SlideGen: Generate tutorial for "Web Scraping"
    SlideGen->>Neo4j: get_prerequisites("Web Scraping")
    Neo4j-->>SlideGen: [Linux, IPython, Functions, File Handling, Pandas]
    SlideGen->>SlideGen: Generate Prerequisites Slide
    SlideGen-->>User: Complete script with accurate prerequisites
```

### Use Case 2: Validate Content Consistency

```mermaid
sequenceDiagram
    participant Evaluator as evaluator_node.py
    participant Neo4j as Neo4j Graph
    participant LLM
    
    Evaluator->>Neo4j: get_concepts_taught("For Loop")
    Neo4j-->>Evaluator: [iteration, range(), loop variable]
    Evaluator->>Neo4j: get_prerequisites_concepts("For Loop")
    Neo4j-->>Evaluator: [variables, operators, lists]
    Evaluator->>LLM: Validate script doesn't reference unknown concepts
    LLM-->>Evaluator: Validation result
```

### Use Case 3: Generate "What's Next" Recommendations

```mermaid
sequenceDiagram
    participant Frontend as React Frontend
    participant API as FastAPI
    participant Neo4j as Neo4j Graph
    
    Frontend->>API: GET /api/recommendations?completed=for-loop
    API->>Neo4j: what_unlocks("For Loop")
    Neo4j-->>API: [While Loop, Conditionals, Dictionaries]
    API-->>Frontend: Recommendations list
    Frontend->>Frontend: Display "What's Next?" section
```

---

## Implementation Plan

```mermaid
gantt
    title Knowledge Graph Implementation Timeline
    dateFormat  YYYY-MM-DD
    
    section Phase 1: Scraping
    Explore ST website structure    :a1, 2024-01-01, 2d
    Build tutorial scraper          :a2, after a1, 3d
    Build prerequisites extractor   :a3, after a1, 2d
    Run full scrape (~1000 tutorials):a4, after a2 a3, 2d
    
    section Phase 2: Neo4j
    Install & configure Neo4j       :b1, after a4, 1d
    Design graph schema             :b2, after b1, 1d
    Build graph population script   :b3, after b2, 2d
    Verify data integrity           :b4, after b3, 1d
    
    section Phase 3: Integration
    Create Neo4j query service      :c1, after b4, 2d
    Integrate with structure_node   :c2, after c1, 1d
    Integrate with evaluator_node   :c3, after c1, 1d
    Build API endpoints             :c4, after c2 c3, 1d
    
    section Phase 4: Polish
    Add caching layer               :d1, after c4, 1d
    Add visualization               :d2, after c4, 2d
    Documentation                   :d3, after d1 d2, 1d
```

---

## File Structure

```
slide-generator/
├── src/
│   ├── services/
│   │   ├── mediawiki_service.py      # Existing
│   │   ├── spoken_tutorial_scraper.py # NEW: Web scraper
│   │   └── neo4j_service.py           # NEW: Graph queries
│   ├── nodes/
│   │   ├── structure_node.py          # Modified: Use graph for prereqs
│   │   └── evaluator_node.py          # Modified: Validate concepts
│   └── graph/
│       ├── schema.py                  # NEW: Graph schema definitions
│       ├── builder.py                 # NEW: Populate graph from scraped data
│       └── queries.py                 # NEW: Cypher query templates
├── docker-compose.yml                 # Modified: Add Neo4j service
└── docs/
    └── knowledge_graph_walkthrough.md # This file
```

---

## Benefits Summary

| Feature | Without Knowledge Graph | With Knowledge Graph |
|---------|------------------------|---------------------|
| **Prerequisites** | Manual guesswork | Auto-populated, accurate |
| **Learning Paths** | None | Full curriculum generation |
| **Recommendations** | None | Smart "What's Next?" |
| **Validation** | Basic LLM check | Concept-level consistency |
| **Content Gaps** | Unknown | Automatically identified |
| **Cross-topic Links** | Manual | Discovered automatically |

---

## Next Steps

1. **Validate Feasibility**: Scrape a small subset (1 topic, ~20 tutorials)
2. **Proof of Concept**: Build simple graph with NetworkX first
3. **Scale Up**: Migrate to Neo4j and scrape full catalog
4. **Integrate**: Connect to Slide Generator nodes
5. **Visualize**: Add interactive graph visualization to frontend

---

## Questions?

Contact the development team or refer to the [Neo4j Documentation](https://neo4j.com/docs/) for advanced graph queries.
