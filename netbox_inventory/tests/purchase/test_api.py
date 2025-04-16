from utilities.testing import APIViewTestCases

from ...models import Purchase, Supplier
from ..custom import APITestCase


class PurchaseTest(
    APITestCase,
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.CreateObjectViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = Purchase
    brief_fields = [
        'date',
        'description',
        'display',
        'id',
        'name',
        'status',
        'supplier',
        'url',
    ]

    bulk_update_data = {
        'description': 'new description',
    }

    @classmethod
    def setUpTestData(cls) -> None:
        supplier1 = Supplier.objects.create(name='Supplier 1')
        Purchase.objects.create(
            name='Purchase 1', supplier=supplier1, status='closed', boms=[]
        )
        Purchase.objects.create(
            name='Purchase 2', supplier=supplier1, status='closed', boms=[]
        )
        Purchase.objects.create(
            name='Purchase 3', supplier=supplier1, status='closed', boms=[]
        )
        cls.create_data = [
            {
                'name': 'Purchase 4',
                'supplier': supplier1.pk,
                'status': 'closed',
                'boms': [],
            },
            {
                'name': 'Purchase 5',
                'supplier': supplier1.pk,
                'status': 'closed',
                'boms': [],
            },
            {
                'name': 'Purchase 6',
                'supplier': supplier1.pk,
                'status': 'closed',
                'boms': [],
            },
        ]
