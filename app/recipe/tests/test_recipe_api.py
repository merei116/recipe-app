from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe, Tag
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse('recipe:recipe-list')

def detail_url(recipe_id):
     return reverse('recipe:recipe-detail', args=[recipe_id])

def create_recipe(user, **params):
    defaults = {
        'title': 'Sample title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe

def create_user(**params):
     return get_user_model().objects.create_user(**params)

class PublicRecipeAPITests(TestCase): 
     
     def setUp(self):
          self.client = APIClient()

     def test_auth_required(self):
          res = self.client.get(RECIPE_URL)
          self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateReсipeApi(TestCase):

     def setUp(self):
          self.client = APIClient()
          self.user = create_user(email='user@example.com', password='testpass123')
          self.client.force_authenticate(self.user)

     def test_retrieve_recipe(self):
          create_recipe(user=self.user)
          create_recipe(user=self.user)
          res = self.client.get(RECIPE_URL)
          recipes = Recipe.objects.all().order_by('-id')
          serializer = RecipeSerializer(recipes, many=True)
          self.assertEqual(res.status_code, status.HTTP_200_OK)
          self.assertEqual(res.data, serializer.data)

     def test_recipe_limited(self):
          other_user = create_user(email='other@example.com', password='password123')
          create_recipe(user=other_user)
          create_recipe(user=self.user)
          res = self.client.get(RECIPE_URL)
          recipes = Recipe.objects.filter(user=self.user)
          serializer = RecipeSerializer(recipes, many=True)
          self.assertEqual(res.status_code, status.HTTP_200_OK)
          self.assertEqual(res.data, serializer.data)



     def test_get_recipe_detail(self):
          recipe = create_recipe(user=self.user)
          url = detail_url(recipe.id)
          res = self.client.get(url)
          serializer = RecipeDetailSerializer(recipe)
          self.assertEqual(res.data, serializer.data)
     
     def test_create_recipe(self):
          payload = {
               'title': 'Sample recipe',
               'time_minutes': 30,
               'price': Decimal('5.99'),
          }
          res = self.client.post(RECIPE_URL, payload)
          self.assertEqual(res.status_code, status.HTTP_201_CREATED)
          recipe = Recipe.objects.get(id=res.data['id'])
          for k, v in payload.items():
               self.assertEqual(getattr(recipe, k), v)
          self.assertEqual(recipe.user, self.user)
     
     def test_partial_update(self):
          original_link = 'https://example.com/recipe.pdf'
          recipe = create_recipe(
               user=self.user,
               title='Sample title',
               link=original_link,
          )
          payload = {'title': 'Sample title'}
          url = detail_url(recipe.id)
          res = self.client.patch(url, payload)
          self.assertEqual(res.status_code, status.HTTP_200_OK)
          recipe.refresh_from_db
          self.assertEqual(recipe.title, payload['title'])
          self.assertEqual(recipe.link, original_link)
          self.assertEqual(recipe.user, self.user)
     
     def test_full_update(self):
          recipe = create_recipe(
               user=self.user,
               title='Sample Title',
               link='https://example.com/recipe.pdf',
               description='Description',
          )
          payload = {
               'title': 'New Recipe',
               'link': 'https://example.com/recipe123.pdf',
               'description': 'Descriprion 2.0',
               'time_minutes': 20,
               'price': Decimal('2.50')
          }
          url = detail_url(recipe.id)
          res = self.client.put(url, payload)
          self.assertEqual(res.status_code, status.HTTP_200_OK)
          recipe.refresh_from_db()
          for k, v in payload.items():
               self.assertEqual(getattr(recipe, k), v)
          self.assertEqual(recipe.user, self.user)
     
     def test_update_error(self):
          new_user = create_user(email='user12@example.com', password='testpass123')
          recipe = create_recipe(user=self.user)
          payload = {'user': new_user.id}
          url = detail_url(recipe.id)
          self.client.patch(url, payload)
          recipe.refresh_from_db()
          self.assertEqual(recipe.user, self.user)


     def test_delete_recipe(self):
          recipe = create_recipe(user=self.user)
          url = detail_url(recipe.id)
          res = self.client.delete(url)
          self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
          self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())
     
     def test_delete_other_error(self):
          new_user = create_user(email='user3@example.com', password='testpass123')
          recipe = create_recipe(user=new_user)
          url = detail_url(recipe.id)
          res = self.client.delete(url)
          self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
          self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

     def test_create_tag(self):
        payload = {
             'title': 'Sample Title',
             'time-minutes': 30,
             'price': Decimal('2.50'),
             'tags': [{'name': 'Thai'},
                      {'name': 'Dinner'}],
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count, 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count, 2)
        for tag in payload.tags:
             exists = recipe.tags.filter(
                  name=tag['name'],
                  user=self.user,
             ).exists
             self.assertTrue(exists)
     
     def test_tags_exists_recipes(self):
          tag = Tag.objects.create(user=self.user, name='Indian')
          payload = {
               'title': 'Sample Title',
               'time-minutes': 30,
               'price': Decimal('2.50'),
               'tags': [{'name': 'Indian'}, {'name': 'breakfast'}],
          }
          res = self.client.post(RECIPE_URL, payload, format='json')
          self.assertEqual(res.status_code, status.HTTP_201_CREATED)
          recipes = Recipe.objects.filter(user=self.user)
          self.assertEqual(recipes.count, 1)
          recipe = recipes[0]
          self.assertEqual(recipe.tags.count, 2)
          self.assertIn(tag, recipe.tags.all())
          for tag in payload.tags:
             exists = recipe.tags.filter(
                  name=tag['name'],
                  user=self.user,
             ).exists
             self.assertTrue(exists)