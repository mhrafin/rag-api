workspace "RAG System" {

    model {
        user = person "User"

        llm = softwareSystem "LLM Provider" "External LLM service" "External"

        rag = softwareSystem "RAG System" {
            frontend = container "Frontend"
            backend = container "Backend"
            database = container "Database" {
                vectordb = component "Vector DB" "" "pgvector"
            }
            worker = container "Background Worker"
            queue = container "Task Queue" "Redis" "" "Queue"
        }

        user -> frontend "Uses"
        frontend -> backend "API Calls"
        backend -> database "Reads from and writes to"
        backend -> queue "Enqueues jobs"
        worker -> queue "Consumes jobs"
        worker -> database "Writes embeddings"
        worker -> llm "Calls for embeddings/Queries"
    }

    views {
        systemContext rag "Diagram1" {
            include *
        }
        container rag "RAG-System" {
            include *
            autolayout lr
        }

        component database "db" {
            include *
        }

        styles {
            element "Person" {
                shape Person
            }
            element "Database" {
                shape Cylinder
            }
            element "External" {
                background #999999
                color #ffffff
            }
        }
    }
}