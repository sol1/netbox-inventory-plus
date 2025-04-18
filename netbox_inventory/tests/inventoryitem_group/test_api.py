from utilities.testing import APIViewTestCases

from ...models import InventoryItemGroup
from ..custom import APITestCase


class InventoryItemGroupTest(
    APITestCase,
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.CreateObjectViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = InventoryItemGroup
    brief_fields = ['_depth', 'description', 'display', 'id', 'name', 'url']
    create_data = [
        {
            'name': 'InventoryItemGroup 4',
        },
        {
            'name': 'InventoryItemGroup 5',
        },
        {
            'name': 'InventoryItemGroup 6',
        },
    ]

    @classmethod
    def setUpTestData(cls) -> None:
        InventoryItemGroup.objects.create(name='InventoryItemGroup 1')
        InventoryItemGroup.objects.create(name='InventoryItemGroup 2')
        InventoryItemGroup.objects.create(name='InventoryItemGroup 3')
