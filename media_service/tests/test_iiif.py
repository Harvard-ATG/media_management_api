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
        return IIIFManifest(manifest_id, **kwargs)

    def get_images_list(self):
        images = [
            {'id': 1, 'is_link': False, 'url': 'http://localhost:8000/loris/foo.jpg', 'label': 'foo.jpg', 'description': '', 'metadata': []},
            {'id': 2, 'is_link': False, 'url': 'http://localhost:8000/loris/bar.jpg', 'label': 'bar.jpg', 'description': '', 'metadata': []},
            {'id': 3, 'is_link': True, 'url': 'http://my.link/image.jpg', 'label': 'image.jpg', 'description': '', 'metadata': []},
            {
                'id': 4,
                'is_link': False,
                'url': 'http://localhost:8000/loris/foo_bar_foo.png',
                'label': 'foo_bar_foo.png',
                'description': 'Foo Bar with Foo Again',
                'metadata': [
                    {"label": "Date", "value": "Once upon a time..."},
                    {"label": "Location", "value": "In a galaxy far far away..."},
                ]
            },
        ]
        return images
    
    def duplicate_image(self, images, image_id, num_duplicates=1):
        '''
        Given a list of images, find an image by ID and duplicate it.
        '''
        image = next(iter([i for i in images if i['id'] == image_id]))
        while num_duplicates > 0:
            images.append(image)
            num_duplicates -= 1
        return images

    def test_create_manifest_with_images(self):
        images = self.get_images_list()
        manifest = self.create_manifest(1, images=self.get_images_list())
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
        manifest = self.create_manifest(manifest_id, label=label, description=description)
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
    
    def test_manifest_has_unique_canvas_ids(self):
        # create a new list of images with duplicates of first and last image
        images = self.get_images_list()
        total_duplicates = 0
        for image_id in (images[0]['id'], images[-1]['id']):
            num_duplicates = 3
            self.duplicate_image(images, image_id, num_duplicates)
            total_duplicates += num_duplicates

        # expect there to be duplicates added to the list
        self.assertEqual(total_duplicates + len(self.get_images_list()), len(images))
        
        # generate manifest from the images
        manifest_id = 1
        manifest_obj = self.create_manifest(manifest_id, images=images)
        manifest_dict = manifest_obj.to_dict()

        # search for duplicate canvas IDs
        seen, dups = set(), []
        for canvas in manifest_dict['sequences'][0]['canvases']:
            canvas_id = canvas['@id']
            if canvas_id not in seen:
                seen.add(canvas_id)
            else:
                dups.append(canvas_id)
        
        # expect there to be no duplicate canvas IDs in the manifest
        self.assertEqual(0, len(dups))
