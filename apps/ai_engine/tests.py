from django.test import TestCase

from apps.ai_engine.models import KnowledgeChunk, KnowledgeDocument
from apps.ai_engine.services.analysis import AIAnalysisService
from apps.ai_engine.services.chunking import (
    ChunkingError,
    KnowledgeChunkingService,
)
from apps.ai_engine.services.context import (
    AIContextBuilder,
    AIContextError,
)
from apps.ai_engine.services.embeddings import (
    BaseEmbeddingProvider,
    EmbeddingError,
    EmbeddingService,
    MockEmbeddingProvider,
)
from apps.ai_engine.services.knowledge_embeddings import (
    KnowledgeEmbeddingError,
    KnowledgeEmbeddingService,
)
from apps.ai_engine.services.llm import (
    LLMError,
    LLMService,
    MockLLMProvider,
)
from apps.organizations.models import Organization


class MockLLMTests(TestCase):
    def test_mock_provider_returns_response(self):
        provider = MockLLMProvider()

        response = provider.generate("Analyze this workflow.")

        self.assertIn("Mock AI response", response)

    def test_empty_prompt_raises_error(self):
        provider = MockLLMProvider()

        with self.assertRaises(LLMError):
            provider.generate("")

    def test_llm_service_uses_default_provider(self):
        service = LLMService()

        response = service.generate("Test prompt.")

        self.assertIn("Mock AI response", response)

    def test_custom_provider_is_used(self):
        class CustomProvider(MockLLMProvider):
            def generate(
                self,
                prompt,
                system_prompt=None,
                temperature=0.2,
                max_tokens=1000,
            ):
                return "Custom response"

        service = LLMService(provider=CustomProvider())

        self.assertEqual(
            service.generate("Test prompt."),
            "Custom response",
        )

    def test_llm_service_rejects_empty_prompt(self):
        service = LLMService()

        with self.assertRaises(LLMError):
            service.generate("")

    def test_llm_service_passes_parameters(self):
        class ParameterProvider(MockLLMProvider):
            def generate(
                self,
                prompt,
                system_prompt=None,
                temperature=0.2,
                max_tokens=1000,
            ):
                self.received = {
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                return "OK"

        provider = ParameterProvider()
        service = LLMService(provider=provider)

        response = service.generate(
            prompt="Analyze",
            system_prompt="System",
            temperature=0.5,
            max_tokens=250,
        )

        self.assertEqual(response, "OK")
        self.assertEqual(
            provider.received["prompt"],
            "Analyze",
        )
        self.assertEqual(
            provider.received["system_prompt"],
            "System",
        )
        self.assertEqual(
            provider.received["temperature"],
            0.5,
        )
        self.assertEqual(
            provider.received["max_tokens"],
            250,
        )

    def test_llm_service_rejects_none_prompt(self):
        service = LLMService()

        with self.assertRaises(LLMError):
            service.generate(None)

    def test_llm_service_rejects_whitespace_prompt(self):
        service = LLMService()

        with self.assertRaises(LLMError):
            service.generate("   ")


class AIContextBuilderTests(TestCase):
    def test_empty_context_raises_error(self):
        builder = AIContextBuilder()

        with self.assertRaises(AIContextError):
            builder.build_prompt_context()

    def test_workflow_context(self):
        class Workflow:
            id = 1
            name = "Order Fulfillment"
            description = "Order processing workflow"
            category = "OPERATIONS"
            status = "ACTIVE"

        builder = AIContextBuilder()

        context = builder.build(workflow=Workflow())

        self.assertEqual(
            context["workflow"]["name"],
            "Order Fulfillment",
        )

    def test_dataframe_is_converted_to_records(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            [
                {
                    "step_name": "Verification",
                    "avg_duration": 12.1,
                }
            ]
        )

        builder = AIContextBuilder()

        context = builder.build(
            duration_analytics=dataframe,
        )

        self.assertEqual(
            context["duration_analytics"][0]["step_name"],
            "Verification",
        )

    def test_dict_is_preserved(self):
        builder = AIContextBuilder()

        data = {
            "total_events": 100,
            "average_duration": 5.2,
        }

        context = builder.build(
            predictions=data,
        )

        self.assertEqual(
            context["predictions"],
            data,
        )

    def test_list_is_preserved(self):
        builder = AIContextBuilder()

        data = [
            {"step": "Verification"},
            {"step": "Packing"},
        ]

        context = builder.build(
            anomalies=data,
        )

        self.assertEqual(
            context["anomalies"],
            data,
        )

    def test_prompt_context_contains_sections(self):
        builder = AIContextBuilder()

        context = builder.build_prompt_context(
            duration_analytics={
                "Verification": 12.1,
            },
            predictions={
                "delay_probability": 0.78,
            },
        )

        self.assertIn(
            "DURATION ANALYTICS",
            context,
        )

        self.assertIn(
            "PREDICTIONS",
            context,
        )

    def test_safe_none_value(self):
        builder = AIContextBuilder()

        context = builder.build(
            explainability=None,
        )

        self.assertNotIn(
            "explainability",
            context,
        )


class AIAnalysisServiceTests(TestCase):
    def test_analysis_returns_response(self):
        service = AIAnalysisService()

        result = service.analyze(
            predictions={
                "delay_probability": 0.78,
            }
        )

        self.assertIn(
            "response",
            result,
        )

        self.assertIn(
            "prompt",
            result,
        )

        self.assertIn(
            "context",
            result,
        )

    def test_analysis_prompt_contains_context(self):
        service = AIAnalysisService()

        result = service.analyze(
            predictions={
                "delay_probability": 0.78,
            }
        )

        self.assertIn(
            "delay_probability",
            result["prompt"],
        )

    def test_custom_system_prompt(self):
        service = AIAnalysisService()

        result = service.analyze(
            predictions={
                "delay_probability": 0.78,
            },
            system_prompt="Custom system instructions.",
        )

        self.assertIn(
            "Mock AI response",
            result["response"],
        )

    def test_analysis_requires_context(self):
        service = AIAnalysisService()

        with self.assertRaises(Exception):
            service.analyze()

    def test_custom_llm_service(self):
        class CustomLLM:
            def generate(
                self,
                prompt,
                system_prompt=None,
                temperature=0.2,
                max_tokens=1000,
            ):
                return "Custom AI result"

        service = AIAnalysisService(
            llm_service=CustomLLM()
        )

        result = service.analyze(
            predictions={
                "delay_probability": 0.78,
            }
        )

        self.assertEqual(
            result["response"],
            "Custom AI result",
        )

    def test_analysis_preserves_context(self):
        service = AIAnalysisService()

        predictions = {
            "delay_probability": 0.78,
        }

        result = service.analyze(
            predictions=predictions,
        )

        self.assertEqual(
            result["context"]["predictions"],
            predictions,
        )


class KnowledgeChunkingServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="RAG Test Organization",
            slug="rag-test-organization",
            industry="Technology",
            description="Organization used for RAG tests.",
        )

        self.document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="Order Fulfillment Knowledge",
            source_type=KnowledgeDocument.SourceType.MANUAL,
            source_reference="test-manual",
            content=(
                "Order Fulfillment is the process of receiving, "
                "verifying, packing, and shipping customer orders. "
                "Verification is an important control step. "
                "Packing prepares the verified order for shipment."
            ),
        )

    def test_chunk_document_creates_chunks(self):
        service = KnowledgeChunkingService(
            chunk_size=80,
            chunk_overlap=10,
        )

        result = service.chunk_document(
            self.document
        )

        self.assertGreater(
            result["chunk_count"],
            1,
        )

        self.assertEqual(
            KnowledgeChunk.objects.filter(
                document=self.document
            ).count(),
            result["chunk_count"],
        )

    def test_chunks_have_correct_document(self):
        service = KnowledgeChunkingService(
            chunk_size=80,
            chunk_overlap=10,
        )

        result = service.chunk_document(
            self.document
        )

        for chunk in result["chunks"]:
            self.assertEqual(
                chunk.document,
                self.document,
            )

    def test_chunk_indexes_are_sequential(self):
        service = KnowledgeChunkingService(
            chunk_size=80,
            chunk_overlap=10,
        )

        service.chunk_document(
            self.document
        )

        indexes = list(
            KnowledgeChunk.objects.filter(
                document=self.document
            ).values_list(
                "chunk_index",
                flat=True,
            )
        )

        self.assertEqual(
            indexes,
            list(range(len(indexes))),
        )

    def test_token_count_is_stored(self):
        service = KnowledgeChunkingService(
            chunk_size=80,
            chunk_overlap=10,
        )

        service.chunk_document(
            self.document
        )

        chunks = KnowledgeChunk.objects.filter(
            document=self.document
        )

        for chunk in chunks:
            self.assertGreater(
                chunk.token_count,
                0,
            )

    def test_existing_chunks_are_replaced(self):
        service = KnowledgeChunkingService(
            chunk_size=80,
            chunk_overlap=10,
        )

        first_result = service.chunk_document(
            self.document
        )

        first_count = first_result[
            "chunk_count"
        ]

        second_result = service.chunk_document(
            self.document
        )

        second_count = second_result[
            "chunk_count"
        ]

        self.assertEqual(
            first_count,
            second_count,
        )

        self.assertEqual(
            KnowledgeChunk.objects.filter(
                document=self.document
            ).count(),
            second_count,
        )

    def test_empty_document_raises_error(self):
        document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="Empty Document",
            source_type=KnowledgeDocument.SourceType.MANUAL,
            content="",
        )

        service = KnowledgeChunkingService()

        with self.assertRaises(ChunkingError):
            service.chunk_document(document)

    def test_invalid_chunk_size_raises_error(self):
        with self.assertRaises(ChunkingError):
            KnowledgeChunkingService(
                chunk_size=0,
            )

    def test_invalid_overlap_raises_error(self):
        with self.assertRaises(ChunkingError):
            KnowledgeChunkingService(
                chunk_size=100,
                chunk_overlap=100,
            )

    def test_invalid_document_type_raises_error(self):
        service = KnowledgeChunkingService()

        with self.assertRaises(ChunkingError):
            service.chunk_document(
                "not a knowledge document"
            )

    def test_small_document_creates_single_chunk(self):
        document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="Small Document",
            source_type=KnowledgeDocument.SourceType.MANUAL,
            content="Short workflow description.",
        )

        service = KnowledgeChunkingService(
            chunk_size=500,
            chunk_overlap=50,
        )

        result = service.chunk_document(
            document
        )

        self.assertEqual(
            result["chunk_count"],
            1,
        )

        self.assertEqual(
            result["chunks"][0].content,
            "Short workflow description.",
        )


class EmbeddingServiceTests(TestCase):
    def test_mock_provider_returns_vector(self):
        provider = MockEmbeddingProvider(
            dimensions=16,
        )

        vector = provider.embed(
            "Order Fulfillment"
        )

        self.assertEqual(
            len(vector),
            16,
        )

    def test_vector_values_are_numeric(self):
        provider = MockEmbeddingProvider()

        vector = provider.embed(
            "Verification step"
        )

        for value in vector:
            self.assertIsInstance(
                value,
                float,
            )

    def test_embedding_is_deterministic(self):
        provider = MockEmbeddingProvider()

        first = provider.embed(
            "Order Fulfillment"
        )

        second = provider.embed(
            "Order Fulfillment"
        )

        self.assertEqual(
            first,
            second,
        )

    def test_different_text_produces_different_vector(self):
        provider = MockEmbeddingProvider()

        first = provider.embed(
            "Order Fulfillment"
        )

        second = provider.embed(
            "Shipping"
        )

        self.assertNotEqual(
            first,
            second,
        )

    def test_vector_is_normalized(self):
        import math

        provider = MockEmbeddingProvider()

        vector = provider.embed(
            "Verification"
        )

        magnitude = math.sqrt(
            sum(value * value for value in vector)
        )

        self.assertAlmostEqual(
            magnitude,
            1.0,
            places=6,
        )

    def test_empty_text_raises_error(self):
        provider = MockEmbeddingProvider()

        with self.assertRaises(EmbeddingError):
            provider.embed("")

    def test_whitespace_text_raises_error(self):
        provider = MockEmbeddingProvider()

        with self.assertRaises(EmbeddingError):
            provider.embed("   ")

    def test_none_text_raises_error(self):
        provider = MockEmbeddingProvider()

        with self.assertRaises(EmbeddingError):
            provider.embed(None)

    def test_invalid_dimensions_raise_error(self):
        with self.assertRaises(EmbeddingError):
            MockEmbeddingProvider(
                dimensions=0,
            )

    def test_embedding_service_uses_default_provider(self):
        service = EmbeddingService()

        vector = service.embed(
            "Order Fulfillment"
        )

        self.assertEqual(
            len(vector),
            32,
        )

    def test_embedding_service_supports_custom_provider(self):
        class CustomProvider(BaseEmbeddingProvider):
            def embed(self, text):
                return [1.0, 2.0, 3.0]

        service = EmbeddingService(
            provider=CustomProvider()
        )

        vector = service.embed(
            "Test"
        )

        self.assertEqual(
            vector,
            [1.0, 2.0, 3.0],
        )

    def test_embed_many_returns_vectors(self):
        service = EmbeddingService()

        vectors = service.embed_many(
            [
                "Order Received",
                "Verification",
                "Shipping",
            ]
        )

        self.assertEqual(
            len(vectors),
            3,
        )

        for vector in vectors:
            self.assertEqual(
                len(vector),
                32,
            )

    def test_embed_many_rejects_none(self):
        service = EmbeddingService()

        with self.assertRaises(EmbeddingError):
            service.embed_many(None)

    def test_embed_many_rejects_invalid_type(self):
        service = EmbeddingService()

        with self.assertRaises(EmbeddingError):
            service.embed_many("not a list")

    def test_embed_many_rejects_empty_text(self):
        service = EmbeddingService()

        with self.assertRaises(EmbeddingError):
            service.embed_many(
                [
                    "Valid text",
                    "",
                ]
            )


class KnowledgeEmbeddingServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Embedding Test Organization",
            slug="embedding-test-organization",
            industry="Technology",
            description="Organization used for embedding tests.",
        )

        self.document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="Order Fulfillment Knowledge",
            source_type=KnowledgeDocument.SourceType.MANUAL,
            source_reference="embedding-test",
            content=(
                "Order fulfillment receives, verifies, "
                "packs, and ships customer orders."
            ),
        )

        self.chunk_one = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=0,
            content=(
                "Order fulfillment receives customer orders."
            ),
            token_count=6,
        )

        self.chunk_two = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=1,
            content=(
                "Verification checks the order before packing."
            ),
            token_count=7,
        )

    def test_embed_chunk_stores_embedding(self):
        service = KnowledgeEmbeddingService()

        result = service.embed_chunk(
            self.chunk_one
        )

        result.refresh_from_db()

        self.assertIsNotNone(
            result.embedding
        )

        self.assertEqual(
            len(result.embedding),
            32,
        )

    def test_embed_chunk_returns_same_chunk(self):
        service = KnowledgeEmbeddingService()

        result = service.embed_chunk(
            self.chunk_one
        )

        self.assertEqual(
            result.pk,
            self.chunk_one.pk,
        )

    def test_embed_document_embeds_all_chunks(self):
        service = KnowledgeEmbeddingService()

        result = service.embed_document(
            self.document
        )

        self.assertEqual(
            result["chunk_count"],
            2,
        )

        chunks = KnowledgeChunk.objects.filter(
            document=self.document
        ).order_by("chunk_index")

        for chunk in chunks:
            self.assertIsNotNone(
                chunk.embedding
            )

            self.assertEqual(
                len(chunk.embedding),
                32,
            )

    def test_embed_chunks_embeds_multiple_chunks(self):
        service = KnowledgeEmbeddingService()

        result = service.embed_chunks(
            [
                self.chunk_one,
                self.chunk_two,
            ]
        )

        self.assertEqual(
            len(result),
            2,
        )

        for chunk in result:
            self.assertIsNotNone(
                chunk.embedding
            )

    def test_embedding_can_be_regenerated(self):
        service = KnowledgeEmbeddingService()

        first = service.embed_chunk(
            self.chunk_one
        )

        first_embedding = list(
            first.embedding
        )

        second = service.embed_chunk(
            self.chunk_one
        )

        second_embedding = list(
            second.embedding
        )

        self.assertEqual(
            first_embedding,
            second_embedding,
        )

    def test_empty_chunk_content_raises_error(self):
        empty_chunk = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=2,
            content="",
            token_count=0,
        )

        service = KnowledgeEmbeddingService()

        with self.assertRaises(
            KnowledgeEmbeddingError
        ):
            service.embed_chunk(
                empty_chunk
            )

    def test_invalid_chunk_type_raises_error(self):
        service = KnowledgeEmbeddingService()

        with self.assertRaises(
            KnowledgeEmbeddingError
        ):
            service.embed_chunk(
                "invalid chunk"
            )

    def test_document_without_chunks_raises_error(self):
        empty_document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="No Chunks Document",
            source_type=KnowledgeDocument.SourceType.MANUAL,
            content="Document without chunks.",
        )

        service = KnowledgeEmbeddingService()

        with self.assertRaises(
            KnowledgeEmbeddingError
        ):
            service.embed_document(
                empty_document
            )

    def test_empty_chunks_list_raises_error(self):
        service = KnowledgeEmbeddingService()

        with self.assertRaises(
            KnowledgeEmbeddingError
        ):
            service.embed_chunks([])

    def test_none_chunks_raises_error(self):
        service = KnowledgeEmbeddingService()

        with self.assertRaises(
            KnowledgeEmbeddingError
        ):
            service.embed_chunks(None)