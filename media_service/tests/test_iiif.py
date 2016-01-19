from django.test import TestCase, RequestFactory
from media_service.models import Course, Collection
from media_service.iiif import CollectionManifestController

class TestCourseManifest(TestCase):
    fixtures = ['test.json']
    def setUp(self):
        self.factory = RequestFactory()

    def test_create_collection_manifest(self):
        pk = 1
        collection = Collection.objects.get(pk=pk)
        self.assertEqual(collection.pk, pk)
        
        request = self.factory.get('/')
        collection_manifest_controller = CollectionManifestController(request, collection)
        data = collection_manifest_controller.get_data()
        self.assertTrue(data)
    