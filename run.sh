brew install ollama
brew services start ollama
ollama pull llama3
ollama pull nomic-embed-text

# this will take a while (10-20 minutes), be patient
docker-compose build
docker-compose up -d