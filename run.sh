brew install ollama
brew services start ollama
ollama pull llama3
ollama pull nomic-embed-text

# this will take a while, be patient
docker-compose build
docker-compose up -d