import os
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.conf import settings
from .helper import ingest_pdf_to_pinecone, get_answer_from_pdf

logger = logging.getLogger(__name__)


@api_view(['POST'])
def upload_pdf(request):
    if 'file' not in request.FILES:
        return Response({"error": "Please upload a file!"}, status=400)

    file_obj = request.FILES['file']
    
    # Temporary save file for processing
    file_path = default_storage.save(f"temp/{file_obj.name}", file_obj)
    full_path = default_storage.path(file_path)

    try:
        ingest_pdf_to_pinecone(full_path)
        return Response({
            "success": True,
            "message": "File received and processed successfully!"
        }, status=200)
    except Exception as e:
        logger.error(f"Error ingesting PDF: {str(e)}")
        return Response({
            "success": False,
            "error": "Failed to process the file. Please try again."
        }, status=500)
    finally:
        # Clean up temporary file
        if os.path.exists(full_path):
            os.remove(full_path)


@api_view(['POST'])
def ask_question(request):
    """
    Chatbot endpoint for answering questions about portfolio.
    
    Request body:
    {
        "question": "What are your skills?"
    }
    
    Response:
    {
        "success": true,
        "answer": "...",
        "message": null
    }
    """
    question = request.data.get('question', '').strip()
    
    # Validation
    if not question:
        return Response({
            "success": False,
            "answer": None,
            "message": "Please ask a question."
        }, status=400)
    
    if len(question) > 500:
        return Response({
            "success": False,
            "answer": None,
            "message": "Question is too long. Please keep it under 500 characters."
        }, status=400)
    
    try:
        logger.info(f"Processing question: {question[:100]}...")
        
        # Get answer from RAG pipeline
        answer = get_answer_from_pdf(question)
        
        if not answer or answer.strip() == "":
            return Response({
                "success": False,
                "answer": None,
                "message": "I couldn't find an answer to your question. Please try rephrasing it."
            }, status=200)
        
        return Response({
            "success": True,
            "answer": answer,
            "message": None
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        
        # Return user-friendly error message
        error_msg = "I'm having trouble processing your question. Please try again later."
        
        return Response({
            "success": False,
            "answer": None,
            "message": error_msg
        }, status=500)