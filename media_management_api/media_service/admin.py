from django.contrib import admin
from .models import MediaStore, Course, Collection, Resource, CollectionResource, UserProfile, Clone

class CollectionsInline(admin.StackedInline):
    extra = 0
    verbose_name = 'Collection'
    model = Collection

class ResourcesInline(admin.StackedInline):
    extra = 0
    verbose_name = 'Resource'
    model = Resource

    def get_queryset(self, request):
        qs = super(ResourcesInline, self).get_queryset(request)
        return qs.select_related('media_store', 'course', 'owner')

class CollectionResourcesInline(admin.StackedInline):
    extra = 0
    verbose_name = 'CollectionResource'
    model = CollectionResource

class MediaStoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'file_md5hash', 'file_type', 'file_size', 'img_width', 'img_height', 'reference_count')
    search_fields = ('file_name', 'file_md5hash')

class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'lti_context_id', 'lti_tool_consumer_instance_guid', 'title')
    search_fields = ('title', 'lti_context_id')
    inlines = (ResourcesInline, CollectionsInline)

class CollectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'sort_order')
    ordering = ('course', 'sort_order')
    search_fields = ('title',)
    inlines = (CollectionResourcesInline,)

    def get_queryset(self, request):
        qs = super(CollectionAdmin, self).get_queryset(request)
        return qs.select_related('course')

class ResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'owner', 'media_store', 'title')
    search_fields = ('title', 'description')

    def get_queryset(self, request):
        qs = super(ResourceAdmin, self).get_queryset(request)
        return qs.select_related('media_store', 'course', 'owner')

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'sis_user_id')
    search_fields = ('sis_user_id', )

    def get_queryset(self, request):
        qs = super(UserProfileAdmin, self).get_queryset(request)
        return qs.select_related('user')

class CloneAdmin(admin.ModelAdmin):
    model = Clone
    list_display = ('id', 'model', 'src_pk', 'dest_pk', 'state', 'created')
    search_fields = ('src_pk', 'dest_pk')

admin.site.register(MediaStore, MediaStoreAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(Resource, ResourceAdmin)
admin.site.register(CollectionResource)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Clone, CloneAdmin)
