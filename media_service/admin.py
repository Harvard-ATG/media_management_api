from django.contrib import admin
from .models import MediaStore, Course, Collection, CourseImage, CollectionImage

class CollectionsInline(admin.StackedInline):
    extra = 0
    verbose_name = 'Collection'
    model = Collection

class CourseImagesInline(admin.StackedInline):
    extra = 0
    verbose_name = 'Course Image'
    model = CourseImage

class CollectionImagesInline(admin.StackedInline):
    extra = 0
    verbose_name = 'Collection Image'
    model = CollectionImage

class MediaStoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'file_md5hash', 'file_type', 'file_size', 'img_width', 'img_height', 'reference_count')

class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'lti_context_id', 'lti_tool_consumer_instance_guid')
    inlines = (CourseImagesInline, CollectionsInline)

class CollectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'sort_order')
    ordering = ('course', 'sort_order')
    inlines = (CollectionImagesInline,)

admin.site.register(MediaStore, MediaStoreAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(CourseImage)
admin.site.register(CollectionImage)
