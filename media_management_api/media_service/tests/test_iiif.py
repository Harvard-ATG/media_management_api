import unittest
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory

from media_management_api.media_service.models import Course, Collection
from media_management_api.media_service.iiif.views import IiifManifestView
from media_management_api.media_service.iiif.objects import IIIFManifest

import json

class IiifManifestViewTest(TestCase):
    fixtures = ['test.json']
    def setUp(self):
        self.factory = RequestFactory()

    def test_manifest(self):
        pk = 1
        collection = Collection.objects.get(pk=pk)
        self.assertEqual(collection.pk, pk)

        request = self.factory.get(reverse('api:iiif:manifest', kwargs={'manifest_id': collection.pk}))
        request.content_type = 'application/json'
        manifest_view = IiifManifestView.as_view()
        response = manifest_view(request, manifest_id=collection.pk)
        self.assertTrue(response.data)

        expected_attrs = ["@context", "@type", "@id", "label", "description", "sequences"]
        self.assertEqual(response.data['@context'], "http://iiif.io/api/presentation/2/context.json")
        self.assertEqual(response.data['@type'], "sc:Manifest")

class IIIFManifestTest(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def create_manifest(self, request, manifest_id, **kwargs):
        return IIIFManifest(request, manifest_id, **kwargs)

    def get_images_list(self):
        images = [
            {'id': 1, 'is_iiif': True, 'url': 'http://localhost:8000/loris/foo.jpg', 'label': 'foo.jpg', 'description': '', 'metadata': []},
            {'id': 2, 'is_iiif': True, 'url': 'http://localhost:8000/loris/bar.jpg', 'label': 'bar.jpg', 'description': '', 'metadata': []},
            {'id': 3, 'is_iiif': False, 'url': 'http://my.link/image.jpg', 'label': 'image.jpg', 'description': '', 'metadata': []},
            {
                'id': 4,
                'is_iiif': True,
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
        manifest_id = 1
        request = self.factory.get(reverse('api:iiif:manifest', kwargs={'manifest_id': manifest_id}))
        manifest = self.create_manifest(request, manifest_id, images=self.get_images_list())
        md = manifest.to_dict()
        iiif_images = [img for img in images if img['is_iiif'] is True]

        self.assertEqual(len(md['sequences']), 1, "should have one default sequence")
        self.assertEqual(len(md['sequences'][0]['canvases']), len(iiif_images), "one canvas per image")
        for idx, canvas in enumerate(md['sequences'][0]['canvases']):
            self.assertEqual(canvas['label'], iiif_images[idx]['label'], "canvas label should match image label")

    def test_manifest_attributes(self):
        label = 'test label'
        description = 'test description'
        manifest_id = 1
        request = self.factory.get(reverse('api:iiif:manifest', kwargs={'manifest_id': manifest_id}))
        manifest = self.create_manifest(request, manifest_id, label=label, description=description)
        md = manifest.to_dict()

        expected_attr = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@type": "sc:Manifest",
            "@id": request.build_absolute_uri(reverse('api:iiif:manifest', kwargs={'manifest_id':manifest_id})),
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
        request = self.factory.get(reverse('api:iiif:manifest', kwargs={'manifest_id': manifest_id}))
        manifest_obj = self.create_manifest(request, manifest_id, images=images)
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
