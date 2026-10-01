### To View C4 Diagrams

The c4 diagrams are stored at docs/01-c4

Step 1: `docker pull structurizr/structurizr`
Step 2: `docker run -it --rm -p 8081:8080 --user "$(id -u):$(id -g)" -v ./docs/01-c4:/usr/local/structurizr structurizr/structurizr local`

Next Visit localhost:8081
