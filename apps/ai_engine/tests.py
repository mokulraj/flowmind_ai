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
from apps.ai_engine.services.prompts import (
    AIPromptBuilder,
)
from apps.ai_engine.services.llm import (
    LLMError,
    LLMService,
    MockLLMProvider,
)
from apps.ai_engine.services.vector_search import (
    KnowledgeVectorSearchService,
    VectorSearchError,
)
from apps.organizations.models import Organization


class MockLLMTests(TestCase):
    def test_mock_provider_returns_response(self):
        provider = MockLLMProvider()

        response = provider.generate(
            "Analyze this workflow."
        )

        self.assertIn(
            "Mock AI response",
            response,
        )

    def test_empty_prompt_raises_error(self):
        provider = MockLLMProvider()

        with self.assertRaises(LLMError):
            provider.generate("")

    def test_llm_service_uses_default_provider(self):
        service = LLMService()

        response = service.generate(
            "Test prompt."
        )

        self.assertIn(
            "Mock AI response",
            response,
        )

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

        service = LLMService(
            provider=CustomProvider()
        )

        self.assertEqual(
            service.generate(
                "Test prompt."
            ),
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

        service = LLMService(
            provider=provider
        )

        response = service.generate(
            prompt="Analyze",
            system_prompt="System",
            temperature=0.5,
            max_tokens=250,
        )

        self.assertEqual(
            response,
            "OK",
        )

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

        context = builder.build(
            workflow=Workflow()
        )

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
            duration_analytics=dataframe
        )

        self.assertEqual(
            context["duration_analytics"][0][
                "step_name"
            ],
            "Verification",
        )

    def test_dict_is_preserved(self):
        builder = AIContextBuilder()

        data = {
            "total_events": 100,
            "average_duration": 5.2,
        }

        context = builder.build(
            predictions=data
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
            anomalies=data
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
            explainability=None
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
            system_prompt=(
                "Custom system instructions."
            ),
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
            predictions=predictions
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
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
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

        second_result = service.chunk_document(
            self.document
        )

        self.assertEqual(
            first_result["chunk_count"],
            second_result["chunk_count"],
        )

        self.assertEqual(
            KnowledgeChunk.objects.filter(
                document=self.document
            ).count(),
            second_result["chunk_count"],
        )

    def test_empty_document_raises_error(self):
        document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="Empty Document",
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
            content="",
        )

        service = KnowledgeChunkingService()

        with self.assertRaises(ChunkingError):
            service.chunk_document(document)

    def test_invalid_chunk_size_raises_error(self):
        with self.assertRaises(ChunkingError):
            KnowledgeChunkingService(
                chunk_size=0
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
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
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
            dimensions=16
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
                dimensions=0
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

        vector = service.embed("Test")

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
            service.embed_many(
                "not a list"
            )

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
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
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

        chunks = (
            KnowledgeChunk.objects
            .filter(
                document=self.document
            )
            .order_by("chunk_index")
        )

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
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
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


class KnowledgeVectorSearchServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Vector Search Organization",
            slug="vector-search-organization",
            industry="Technology",
            description="Organization used for vector search tests.",
        )

        self.other_organization = Organization.objects.create(
            name="Other Organization",
            slug="other-vector-search-organization",
            industry="Technology",
            description="Organization for tenant isolation tests.",
        )

        self.document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="Order Fulfillment Knowledge",
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
            content="Order fulfillment process.",
        )

        self.other_document = KnowledgeDocument.objects.create(
            organization=self.other_organization,
            title="Other Organization Knowledge",
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
            content="Other organization process.",
        )

        self.chunk_one = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=0,
            content="Order verification process.",
            token_count=3,
        )

        self.chunk_two = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=1,
            content="Packing and shipping process.",
            token_count=4,
        )

        self.other_chunk = KnowledgeChunk.objects.create(
            document=self.other_document,
            chunk_index=0,
            content="Other organization information.",
            token_count=3,
        )

        embedding_service = EmbeddingService()

        KnowledgeEmbeddingService(
            embedding_service=embedding_service
        ).embed_chunks(
            [
                self.chunk_one,
                self.chunk_two,
                self.other_chunk,
            ]
        )

    def test_search_returns_results(self):
        service = KnowledgeVectorSearchService()

        results = service.search(
            query="Order verification",
            organization=self.organization,
        )

        self.assertGreater(
            len(results),
            0,
        )

    def test_search_results_have_required_fields(self):
        service = KnowledgeVectorSearchService()

        results = service.search(
            query="Order verification",
            organization=self.organization,
        )

        result = results[0]

        self.assertIn(
            "chunk",
            result,
        )

        self.assertIn(
            "document",
            result,
        )

        self.assertIn(
            "similarity",
            result,
        )

    def test_results_are_sorted_by_similarity(self):
        service = KnowledgeVectorSearchService()

        results = service.search(
            query="Order verification",
            organization=self.organization,
            top_k=5,
        )

        similarities = [
            result["similarity"]
            for result in results
        ]

        self.assertEqual(
            similarities,
            sorted(
                similarities,
                reverse=True,
            ),
        )

    def test_top_k_limits_results(self):
        service = KnowledgeVectorSearchService()

        results = service.search(
            query="workflow",
            organization=self.organization,
            top_k=1,
        )

        self.assertLessEqual(
            len(results),
            1,
        )

    def test_search_is_tenant_isolated(self):
        service = KnowledgeVectorSearchService()

        results = service.search(
            query="Other organization information",
            organization=self.organization,
            top_k=10,
        )

        returned_chunks = [
            result["chunk"]
            for result in results
        ]

        self.assertNotIn(
            self.other_chunk,
            returned_chunks,
        )

    def test_search_excludes_chunks_without_embeddings(self):
        chunk_without_embedding = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=2,
            content="Chunk without an embedding.",
            token_count=4,
        )

        service = KnowledgeVectorSearchService()

        results = service.search(
            query="Chunk without embedding",
            organization=self.organization,
            top_k=10,
        )

        returned_chunks = [
            result["chunk"]
            for result in results
        ]

        self.assertNotIn(
            chunk_without_embedding,
            returned_chunks,
        )

    def test_empty_query_raises_error(self):
        service = KnowledgeVectorSearchService()

        with self.assertRaises(
            VectorSearchError
        ):
            service.search(
                query="",
                organization=self.organization,
            )

    def test_none_query_raises_error(self):
        service = KnowledgeVectorSearchService()

        with self.assertRaises(
            VectorSearchError
        ):
            service.search(
                query=None,
                organization=self.organization,
            )

    def test_none_organization_raises_error(self):
        service = KnowledgeVectorSearchService()

        with self.assertRaises(
            VectorSearchError
        ):
            service.search(
                query="verification",
                organization=None,
            )

    def test_invalid_top_k_raises_error(self):
        service = KnowledgeVectorSearchService()

        with self.assertRaises(
            VectorSearchError
        ):
            service.search(
                query="verification",
                organization=self.organization,
                top_k=0,
            )

    def test_cosine_similarity_identical_vectors(self):
        similarity = (
            KnowledgeVectorSearchService
            ._cosine_similarity(
                [1.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
            )
        )

        self.assertAlmostEqual(
            similarity,
            1.0,
            places=6,
        )

    def test_cosine_similarity_orthogonal_vectors(self):
        similarity = (
            KnowledgeVectorSearchService
            ._cosine_similarity(
                [1.0, 0.0],
                [0.0, 1.0],
            )
        )

        self.assertAlmostEqual(
            similarity,
            0.0,
            places=6,
        )

    def test_cosine_similarity_rejects_different_dimensions(self):
        with self.assertRaises(
            VectorSearchError
        ):
            KnowledgeVectorSearchService._cosine_similarity(
                [1.0, 0.0],
                [1.0, 0.0, 0.0],
            )

    def test_cosine_similarity_rejects_zero_vector(self):
        with self.assertRaises(
            VectorSearchError
        ):
            KnowledgeVectorSearchService._cosine_similarity(
                [0.0, 0.0],
                [1.0, 0.0],
            )


class RAGAnalysisIntegrationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="RAG Integration Organization",
            slug="rag-integration-organization",
            industry="Technology",
            description="Organization used for RAG integration tests.",
        )

        self.document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="Verification Knowledge",
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
            content=(
                "Verification checks payment information "
                "before an order proceeds to packing."
            ),
        )

        self.chunk = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=0,
            content=(
                "Verification checks payment information "
                "before an order proceeds to packing."
            ),
            token_count=10,
        )

        KnowledgeEmbeddingService().embed_chunk(
            self.chunk
        )

    def test_analysis_can_use_rag(self):
        service = AIAnalysisService()

        result = service.analyze(
            predictions={
                "delay_probability": 0.78,
            },
            query="How does verification work?",
            organization=self.organization,
        )

        self.assertIn(
            "retrieved_knowledge",
            result,
        )

        self.assertGreater(
            len(result["retrieved_knowledge"]),
            0,
        )

    def test_rag_context_is_in_prompt(self):
        service = AIAnalysisService()

        result = service.analyze(
            predictions={
                "delay_probability": 0.78,
            },
            query="How does verification work?",
            organization=self.organization,
        )

        self.assertIn(
            "RETRIEVED KNOWLEDGE",
            result["prompt"],
        )

        self.assertIn(
            "Verification checks payment information",
            result["prompt"],
        )

    def test_rag_context_is_returned(self):
        service = AIAnalysisService()

        result = service.analyze(
            query="How does verification work?",
            organization=self.organization,
        )

        self.assertIn(
            "retrieved_knowledge",
            result["context"],
        )

        retrieved = result["context"][
            "retrieved_knowledge"
        ]

        self.assertGreater(
            len(retrieved),
            0,
        )

        self.assertEqual(
            retrieved[0]["document_title"],
            "Verification Knowledge",
        )

    def test_query_requires_organization(self):
        service = AIAnalysisService()

        with self.assertRaises(
            Exception
        ):
            service.analyze(
                predictions={
                    "delay_probability": 0.78,
                },
                query="verification",
            )

    def test_analysis_without_query_still_works(self):
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

        self.assertIsNone(
            result["retrieved_knowledge"]
        )
        
        
class AIWorkflowAssistantTests(TestCase):
    def setUp(self):
        from apps.ai_engine.services.assistant import (
            AIWorkflowAssistant,
            AIWorkflowAssistantError,
        )

        self.AIWorkflowAssistant = AIWorkflowAssistant
        self.AIWorkflowAssistantError = (
            AIWorkflowAssistantError
        )

        self.organization = Organization.objects.create(
            name="Assistant Test Organization",
            slug="assistant-test-organization",
            industry="Technology",
            description="Organization used for assistant tests.",
        )

        self.document = KnowledgeDocument.objects.create(
            organization=self.organization,
            title="Assistant Knowledge",
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
            content=(
                "Verification checks payment information "
                "before an order proceeds to packing."
            ),
        )

        self.chunk = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=0,
            content=(
                "Verification checks payment information "
                "before an order proceeds to packing."
            ),
            token_count=10,
        )

        KnowledgeEmbeddingService().embed_chunk(
            self.chunk
        )

    def test_assistant_can_answer_analysis_question(self):
        assistant = self.AIWorkflowAssistant()

        result = assistant.ask(
            query="How does verification work?",
            organization=self.organization,
            predictions={
                "delay_probability": 0.78,
            },
        )

        self.assertIn(
            "response",
            result,
        )

        self.assertIn(
            "query",
            result,
        )

        self.assertEqual(
            result["query"],
            "How does verification work?",
        )

    def test_assistant_uses_rag(self):
        assistant = self.AIWorkflowAssistant()

        result = assistant.ask(
            query="How does verification work?",
            organization=self.organization,
        )

        self.assertGreater(
            len(result["retrieved_knowledge"]),
            0,
        )

    def test_assistant_returns_context(self):
        assistant = self.AIWorkflowAssistant()

        result = assistant.ask(
            query="How does verification work?",
            organization=self.organization,
            predictions={
                "delay_probability": 0.78,
            },
        )

        self.assertIn(
            "predictions",
            result["context"],
        )

        self.assertIn(
            "retrieved_knowledge",
            result["context"],
        )

    def test_assistant_can_use_analytics_without_query(self):
        assistant = self.AIWorkflowAssistant()

        result = assistant.ask(
            predictions={
                "delay_probability": 0.78,
            },
        )

        self.assertIsNotNone(
            result["query"]
        )

        self.assertIn(
            "response",
            result,
        )

        self.assertIsNone(
            result["retrieved_knowledge"]
        )

    def test_empty_query_raises_error(self):
        assistant = self.AIWorkflowAssistant()

        with self.assertRaises(
            self.AIWorkflowAssistantError
        ):
            assistant.ask(
                query="   ",
                organization=self.organization,
            )

    def test_query_without_organization_raises_error(self):
        assistant = self.AIWorkflowAssistant()

        with self.assertRaises(
            self.AIWorkflowAssistantError
        ):
            assistant.ask(
                query="What is verification?"
            )

    def test_default_analysis_query_is_used(self):
        assistant = self.AIWorkflowAssistant()

        result = assistant.ask(
            predictions={
                "delay_probability": 0.78,
            },
        )

        self.assertEqual(
            result["query"],
            assistant.DEFAULT_QUERY,
        )

    def test_custom_analysis_service_is_supported(self):
        class CustomAnalysisService:
            def analyze(
                self,
                **kwargs,
            ):
                return {
                    "response": "Custom assistant response",
                    "context": {
                        "custom": True,
                    },
                    "retrieved_knowledge": None,
                    "prompt": "Custom prompt",
                }

        assistant = self.AIWorkflowAssistant(
            analysis_service=CustomAnalysisService()
        )

        result = assistant.ask(
            predictions={
                "delay_probability": 0.78,
            },
        )

        self.assertEqual(
            result["response"],
            "Custom assistant response",
        )

        self.assertEqual(
            result["context"]["custom"],
            True,
        )

    def test_query_is_trimmed(self):
        assistant = self.AIWorkflowAssistant()

        result = assistant.ask(
            query="  What is verification?  ",
            organization=self.organization,
        )

        self.assertEqual(
            result["query"],
            "What is verification?",
        )
        
        
class AIPromptBuilderTests(TestCase):
    def setUp(self):
        from apps.ai_engine.services.prompts import (
            AIPromptBuilder,
            AIPromptError,
        )

        self.AIPromptBuilder = AIPromptBuilder
        self.AIPromptError = AIPromptError

        self.builder = AIPromptBuilder()

        self.context = (
            "WORKFLOW\n"
            "{'name': 'Order Fulfillment'}"
        )

    def test_workflow_analysis_prompt(self):
        prompt = self.builder.build(
            self.AIPromptBuilder.WORKFLOW_ANALYSIS,
            self.context,
        )

        self.assertIn(
            "Analyze the workflow context",
            prompt,
        )

        self.assertIn(
            self.context,
            prompt,
        )

    def test_bottleneck_analysis_prompt(self):
        prompt = self.builder.build(
            self.AIPromptBuilder.BOTTLENECK_ANALYSIS,
            self.context,
        )

        self.assertIn(
            "bottleneck",
            prompt.lower(),
        )

    def test_anomaly_analysis_prompt(self):
        prompt = self.builder.build(
            self.AIPromptBuilder.ANOMALY_ANALYSIS,
            self.context,
        )

        self.assertIn(
            "anomaly",
            prompt.lower(),
        )

    def test_prediction_analysis_prompt(self):
        prompt = self.builder.build(
            self.AIPromptBuilder.PREDICTION_ANALYSIS,
            self.context,
        )

        self.assertIn(
            "prediction",
            prompt.lower(),
        )

    def test_operational_summary_prompt(self):
        prompt = self.builder.build(
            self.AIPromptBuilder.OPERATIONAL_SUMMARY,
            self.context,
        )

        self.assertIn(
            "operational summary",
            prompt.lower(),
        )

    def test_rag_question_prompt(self):
        prompt = self.builder.build(
            self.AIPromptBuilder.RAG_QUESTION,
            self.context,
        )

        self.assertIn(
            "retrieved knowledge",
            prompt.lower(),
        )

    def test_all_prompt_types_are_supported(self):
        prompt_types = [
            self.AIPromptBuilder.WORKFLOW_ANALYSIS,
            self.AIPromptBuilder.BOTTLENECK_ANALYSIS,
            self.AIPromptBuilder.ANOMALY_ANALYSIS,
            self.AIPromptBuilder.PREDICTION_ANALYSIS,
            self.AIPromptBuilder.OPERATIONAL_SUMMARY,
            self.AIPromptBuilder.RAG_QUESTION,
        ]

        for prompt_type in prompt_types:
            prompt = self.builder.build(
                prompt_type,
                self.context,
            )

            self.assertTrue(
                prompt.strip()
            )

    def test_invalid_prompt_type_raises_error(self):
        with self.assertRaises(
            self.AIPromptError
        ):
            self.builder.build(
                "invalid_prompt_type",
                self.context,
            )

    def test_none_context_raises_error(self):
        with self.assertRaises(
            self.AIPromptError
        ):
            self.builder.build(
                self.AIPromptBuilder.WORKFLOW_ANALYSIS,
                None,
            )

    def test_empty_context_raises_error(self):
        with self.assertRaises(
            self.AIPromptError
        ):
            self.builder.build(
                self.AIPromptBuilder.WORKFLOW_ANALYSIS,
                "   ",
            )


class AIPromptIntegrationTests(TestCase):
    def test_analysis_returns_prompt_type(self):
        service = AIAnalysisService()

        result = service.analyze(
            predictions={
                "delay_probability": 0.78,
            }
        )

        self.assertEqual(
            result["prompt_type"],
            "prediction_analysis",
        )

    def test_bottleneck_context_selects_bottleneck_prompt(self):
        service = AIAnalysisService()

        result = service.analyze(
            bottlenecks=[
                {
                    "step_name": "Verification",
                    "severity": "HIGH",
                }
            ]
        )

        self.assertEqual(
            result["prompt_type"],
            "bottleneck_analysis",
        )

        self.assertIn(
            "bottleneck",
            result["prompt"].lower(),
        )

    def test_anomaly_context_selects_anomaly_prompt(self):
        service = AIAnalysisService()

        result = service.analyze(
            anomalies=[
                {
                    "step_name": "Verification",
                    "is_anomaly": True,
                }
            ]
        )

        self.assertEqual(
            result["prompt_type"],
            "anomaly_analysis",
        )

    def test_query_selects_rag_prompt(self):
        organization = Organization.objects.create(
            name="Prompt RAG Organization",
            slug="prompt-rag-organization",
            industry="Technology",
            description="Organization used for prompt RAG tests.",
        )

        document = KnowledgeDocument.objects.create(
            organization=organization,
            title="Prompt Knowledge",
            source_type=(
                KnowledgeDocument.SourceType.MANUAL
            ),
            content=(
                "Verification checks payment information."
            ),
        )

        chunk = KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            content=(
                "Verification checks payment information."
            ),
            token_count=5,
        )

        KnowledgeEmbeddingService().embed_chunk(
            chunk
        )

        service = AIAnalysisService()

        result = service.analyze(
            query="What does verification do?",
            organization=organization,
        )

        self.assertEqual(
            result["prompt_type"],
            "rag_question",
        )

        self.assertIn(
            "retrieved knowledge",
            result["prompt"].lower(),
        )

    def test_explicit_prompt_type_is_respected(self):
        service = AIAnalysisService()

        result = service.analyze(
            predictions={
                "delay_probability": 0.78,
            },
            prompt_type=(
                AIPromptBuilder.OPERATIONAL_SUMMARY
            ),
        )

        self.assertEqual(
            result["prompt_type"],
            AIPromptBuilder.OPERATIONAL_SUMMARY,
        )

        self.assertIn(
            "operational summary",
            result["prompt"].lower(),
        )