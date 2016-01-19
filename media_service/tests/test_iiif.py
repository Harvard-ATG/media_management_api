import unittest
from django.test import TestCase, RequestFactory
from media_service.models import Course, Collection
from media_service.iiif import CollectionManifestController, IIIFManifest

class TestCollectionManifestController(TestCase):
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

        expected_attrs = ["@context", "@type", "@id", "label", "description", "sequences"]
        self.assertEqual(sorted(data.keys()), sorted(expected_attrs))
        self.assertEqual(data['@context'], "http://iiif.io/api/presentation/2/context.json")
        self.assertEqual(data['@type'], "sc:Manifest")
        
class IIIFManifestTest(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def create_manifest(self, manifest_id, **kwargs):
        request = self.factory.get('/')
        return request, IIIFManifest(manifest_id, **kwargs)

    def get_images_list(self):
        images = [
            {'id': 1, 'is_link': False, 'url': 'http://localhost:8000/loris/foo.jpg', 'label': 'foo.jpg'},
            {'id': 2, 'is_link': False, 'url': 'http://localhost:8000/loris/bar.jpg', 'label': 'bar.jpg'},
            {'id': 3, 'is_link': True, 'url': 'http://my.link/image.jpg', 'label': 'image.jpg'},
        ]
        return images

    def test_create_manifest_with_images(self):
        images = self.get_images_list()
        request, manifest = self.create_manifest(1, images=self.get_images_list())
        md = manifest.to_dict()
        
        non_link_images = [img for img in images if img['is_link'] is False]

        self.assertEqual(len(md['sequences']), 1, "should have one default sequence")
        self.assertEqual(len(md['sequences'][0]['canvases']), len(non_link_images), "one canvas per image")
        for idx, canvas in enumerate(md['sequences'][0]['canvases']): 
            self.assertEqual(canvas['label'], non_link_images[idx]['label'], "canvas label should match image label")

    def test_manifest_attributes(self):
        label = 'test label'
        description = 'test description'
        manifest_id = 1
        request, manifest = self.create_manifest(manifest_id, label=label, description=description)
        md = manifest.to_dict()
        
        expected_attr = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@type": "sc:Manifest",
            "@id": '?manifest_id=%s&object_type=manifest' % manifest_id,
            "label": label,
            "description": description,
            "sequences": []
        }
        
        for key in expected_attr.keys():
            self.assertTrue(key in md, "manifest should have a %s attribute" % key)
            self.assertEqual(md[key], expected_attr[key])
    