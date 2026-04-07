"""
Django management command to embed portfolio data into Pinecone vector database.
Usage: python manage.py embed_portfolio
"""

import os
import yaml
from django.core.management.base import BaseCommand
from django.conf import settings
from decouple import config
from pathlib import Path

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


class Command(BaseCommand):
    help = "Embed portfolio data from YAML file into Pinecone vector database"

    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.SUCCESS("Starting portfolio data embedding..."))
            
            # Configuration
            pinecone_api_key = config('PINECONE_API_KEY')
            index_name = config('PINECONE_INDEX_NAME', default='chat-pdf-index')
            openrouter_api_key = config('OPENROUTER_API_KEY')
            
            # Load portfolio data
            portfolio_file = Path(__file__).resolve().parent.parent.parent / 'portfolio_data.yaml'
            
            if not portfolio_file.exists():
                self.stdout.write(self.style.ERROR(f"Portfolio data file not found: {portfolio_file}"))
                return
            
            with open(portfolio_file, 'r', encoding='utf-8') as f:
                portfolio_data = yaml.safe_load(f)
            
            self.stdout.write(self.style.SUCCESS(f"✓ Loaded portfolio data from {portfolio_file}"))
            
            # Initialize Pinecone
            pc = Pinecone(api_key=pinecone_api_key)
            
            # Ensure index exists
            index_names = pc.list_indexes().names()
            if index_name not in index_names:
                self.stdout.write(self.style.WARNING(f"Creating Pinecone index: {index_name}"))
                pc.create_index(
                    name=index_name,
                    dimension=1536,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                self.stdout.write(self.style.SUCCESS(f"✓ Created index: {index_name}"))
            
            index = pc.Index(index_name)
            
            # Clear old portfolio data (namespace isolation)
            namespace = "portfolio"
            try:
                index.delete(delete_all=True, namespace=namespace)
                self.stdout.write(self.style.SUCCESS(f"✓ Cleared old data from namespace: {namespace}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Note: Could not clear namespace (may not exist): {e}"))
            
            # Initialize embeddings
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=openrouter_api_key,
                openai_api_base="https://openrouter.ai/api/v1"
            )
            
            self.stdout.write(self.style.SUCCESS("✓ Initialized OpenAI embeddings"))
            
            # Extract and prepare documents
            documents_text = self._extract_portfolio_content(portfolio_data)
            
            # Split into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            chunks = text_splitter.split_documents([
                type('Document', (), {'page_content': doc, 'metadata': {'source': 'portfolio'}})()
                for doc in documents_text
            ])
            
            self.stdout.write(self.style.SUCCESS(f"✓ Split into {len(chunks)} chunks"))
            
            # Embed and store in Pinecone
            vectorstore = PineconeVectorStore.from_documents(
                chunks,
                embeddings,
                index_name=index_name,
                namespace=namespace
            )
            
            self.stdout.write(self.style.SUCCESS(
                f"✓ Successfully embedded {len(chunks)} portfolio chunks into Pinecone"
            ))
            self.stdout.write(self.style.SUCCESS("✓ Portfolio data embedding completed successfully!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error embedding portfolio data: {str(e)}"))
            raise

    def _extract_portfolio_content(self, portfolio_data):
        """Extract text from portfolio YAML in a structured way"""
        documents = []
        
        portfolio = portfolio_data.get('portfolio', {})
        
        # About section
        about = portfolio.get('about', {})
        for section in about.get('sections', []):
            title = section.get('title', '')
            content = section.get('content', '')
            if content:
                doc = f"ABOUT: {title}\n\n{content.strip()}"
                documents.append(doc)
        
        # Skills section
        skills = portfolio.get('skills', {})
        for section in skills.get('sections', []):
            category = section.get('category', '')
            skills_list = section.get('skills', [])
            
            skill_text = f"SKILLS - {category}:\n"
            for skill in skills_list:
                name = skill.get('name', '')
                level = skill.get('level', '')
                description = skill.get('description', '')
                skill_text += f"\n{name} ({level}): {description}"
            
            documents.append(skill_text)
        
        # Projects section
        projects = portfolio.get('projects', {})
        for section in projects.get('sections', []):
            title = section.get('title', '')
            description = section.get('description', '')
            technologies = section.get('technologies', [])
            features = section.get('key_features', [])
            status = section.get('status', '')
            
            project_text = f"PROJECT: {title}\n"
            project_text += f"Status: {status}\n\n"
            project_text += f"Description:\n{description}\n"
            project_text += f"\nTechnologies: {', '.join(technologies)}\n"
            project_text += f"Key Features:\n"
            for feature in features:
                project_text += f"- {feature}\n"
            
            documents.append(project_text)
        
        # Experience section
        experience = portfolio.get('experience', {})
        for section in experience.get('sections', []):
            title = section.get('title', '')
            content = section.get('content', '')
            if content:
                doc = f"EXPERIENCE - {title}\n\n{content.strip()}"
                documents.append(doc)
        
        # Contact section
        contact = portfolio.get('contact', {})
        for section in contact.get('sections', []):
            title = section.get('title', '')
            content = section.get('content', '')
            if content:
                doc = f"CONTACT: {title}\n\n{content.strip()}"
                documents.append(doc)
        
        return documents
