import unittest
from media_service.models import MediaStore

class TestMediaStore(unittest.TestCase):
    test_items = [
        {
            "file_name": "foo.jpg",
            "file_size": 51200,
            "file_md5hash": '4603090cae0c1ad78285207ffe9fb574',
            "file_extension": "jpg",
            "file_type": "image/jpeg",
            "img_width": 400,
            "img_height": 300,
        },
        {
            "file_name": "bar.gif",
            "file_size": 1024,
            "file_md5hash": '3213090cae0c1ad78285207ffe9fb456',
            "file_extension": "gif",
            "file_type": "image/gif",
            "img_width": 24,
            "img_height": 24,            
        }
    ]
    
    @classmethod
    def setUpClass(cls):
        for test_item in cls.test_items:
            instance = MediaStore(**test_item)
            instance.save()
            test_item['pk'] = instance.pk

    @classmethod
    def tearDownClass(cls):
        MediaStore.objects.filter(pk__in=[x['pk'] for x in cls.test_items]).delete()
 
    def test_get_image(self):
        queryset = MediaStore.objects.filter(pk__in=[x['pk'] for x in self.test_items])
        self.assertTrue(len(queryset) > 0)
        for media_store in queryset:
            full_actual = media_store.get_image_full()
            thumb_actual = media_store.get_image_thumb()
            thumb_w, thumb_h = media_store.calc_thumb_size()
            self.assertEqual(full_actual['width'], media_store.img_width)
            self.assertEqual(full_actual['height'], media_store.img_height)
            self.assertTrue(full_actual['url'])
            self.assertEqual(thumb_actual['width'], thumb_w)
            self.assertEqual(thumb_actual['height'], thumb_h)
            self.assertTrue(thumb_actual['url'])
