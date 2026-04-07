from django.test import SimpleTestCase

from . import helper


class HelperImportTests(SimpleTestCase):
    def test_helper_module_imports(self):
        self.assertTrue(hasattr(helper, "ingest_pdf_to_pinecone"))
        self.assertTrue(hasattr(helper, "get_answer_from_pdf"))

    def test_fallback_embeddings_are_available(self):
        embeddings = helper.get_embeddings()

        self.assertTrue(hasattr(embeddings, "embed_documents"))
        self.assertTrue(hasattr(embeddings, "embed_query"))

        vector = embeddings.embed_query("hello world")
        self.assertEqual(len(vector), 384)
        self.assertTrue(any(value != 0 for value in vector))
