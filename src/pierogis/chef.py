import argparse
import uuid

from pierogis import Dish, Pierogi, Sort, Quantize, Threshold, Recipe


class DishDescription:
    def __init__(self, ingredients=None, seasoning_links=None, recipes=None, file_links=None):
        if ingredients is None:
            ingredients = {}
        if seasoning_links is None:
            seasoning_links = {}
        if recipes is None:
            recipes = []
        if file_links is None:
            file_links = {}

        self.ingredients = ingredients
        self.seasoning_links = seasoning_links
        self.recipes = recipes
        self.file_links = file_links

    def add_ingredient(self, ingredient_desc):
        pierogi_uuid = str(uuid.uuid4())

        self.ingredients[pierogi_uuid] = ingredient_desc

        return pierogi_uuid

    def add_file_link(self, path):
        file_uuid = str(uuid.uuid4())
        self.file_links[file_uuid] = path

        return file_uuid

    def add_recipe(self, recipe):
        self.recipes.append(recipe)

    def add_seasoning(self, target_uuid, season_uuid):
        self.seasoning_links[target_uuid] = season_uuid


class Chef:
    ingredient_classes = {
        'pierogi': Pierogi,
        'sort': Sort,
        'quantize': Quantize,
        'threshold': Threshold
    }

    # seasoning_classes = {
    #     'threshold': Threshold
    # }

    def __init__(self):
        sort_parser = argparse.ArgumentParser(add_help=False)
        sort_parser.set_defaults(add_dish_desc=self.add_sort_desc)
        sort_parser.add_argument('-t', '--turns', default=0, type=int)
        sort_parser.add_argument('-l', '--lower-threshold', default=64, type=int,
                                 help='Pixels with lightness below this threshold will not get sorted')
        sort_parser.add_argument('-u', '--upper-threshold', default=180, type=int,
                                 help='Pixels with lightness above this threshold will not get sorted')

        quantize_parser = argparse.ArgumentParser(add_help=False)
        quantize_parser.set_defaults(add_dish_desc=self.add_quantize_desc)
        quantize_parser.add_argument('-k', '--colors', default=8)

        recipe_parser = argparse.ArgumentParser(add_help=False)
        recipe_parser.set_defaults(add_dish_desc=self.add_recipe_desc)
        recipe_parser.add_argument('recipe_path', type=str, default='./recipe.txt')

        self.menu = {
            'sort': sort_parser,
            'quantize': quantize_parser,
            'recipe': recipe_parser
        }

    def read_recipe(self, dish_description, recipe_text):
        lines = recipe_text.split(';')

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        for command, command_parser in self.menu.items():
            subparsers.add_parser(command, parents=[command_parser], add_help=False)

        for i in range(len(lines)):
            line = lines[i]
            phrases = line.split()

            parsed, unknown = parser.parse_known_args(phrases)
            parsed_vars = vars(parsed)
            add_dish_desc = parsed_vars.pop('add_dish_desc')

            dish_description = add_dish_desc(dish_description, **parsed_vars)

        return dish_description

    def add_recipe_desc(self, dish_description, recipe_path, **kwargs):
        try:
            with open(recipe_path) as recipe_file:
                dish_description = self.read_recipe(dish_description, recipe_file.read())

            return dish_description

        except Exception as err:
            print(err)

    def add_pierogi_desc(self, dish_description, image_path):
        file_uuid = dish_description.add_file_link(image_path)

        ingredient_desc = {
            'type': 'pierogi',
            'args': [],
            'kwargs': {
                'file': file_uuid
            }
        }

        pierogi_uuid = dish_description.add_ingredient(ingredient_desc)

        dish_description.add_recipe([pierogi_uuid])

        return dish_description

    def add_sort_desc(self, dish_desc, **kwargs):
        """
        Sort pixels in an image by intensity
        """
        try:
            # seasoning is for things that process but don't return a array
            sort_dict = {
                'type': 'sort',
                'args': [],
                'kwargs': {
                    **kwargs
                }
            }
            sort_uuid = dish_desc.add_ingredient(sort_dict)

            # check for implied threshold
            lower_threshold = kwargs.pop('lower_threshold')
            upper_threshold = kwargs.pop('upper_threshold')
            if (lower_threshold is not None) or (upper_threshold is not None):
                threshold_dict = {
                    'type': 'threshold',
                    'args': [],
                    'kwargs': {
                        'lower_threshold': lower_threshold,
                        'upper_threshold': upper_threshold
                    }
                }
                season_uuid = dish_desc.add_ingredient(threshold_dict)
                dish_desc.add_seasoning(sort_uuid, season_uuid)

            dish_desc.add_recipe([sort_uuid])

            return dish_desc

        except Exception as err:
            print(err)

    def add_quantize_desc(self, dish_desc, **kwargs):
        """
        Create a description of a quantize recipe
        """
        quantize_dict = {
            'type': 'quantize',
            'args': [],
            'kwargs': {
                **kwargs
            }
        }
        quantize_uuid = dish_desc.add_ingredient(quantize_dict)

        dish_desc.add_recipe([quantize_uuid])

        return dish_desc

    def cook_dish_desc(self, dish_description):
        """
        Cook a dish from a series of descriptive dicts
        """
        ingredient_descs = dish_description.ingredients
        file_links = dish_description.file_links
        recipe_orders = dish_description.recipes
        seasoning_links = dish_description.seasoning_links

        ingredients = {}
        target = None

        for ingredient_name, ingredient_desc in ingredient_descs.items():
            # if path is one of the kwargs, we should look it up in the linking paths dictionary
            file_name = ingredient_desc['kwargs'].get('file')
            if file_name is not None:
                file = file_links[file_name]
                ingredient_desc['kwargs']['file'] = file

            # now create an ingredient as specified in the description
            ingredient_class = self.ingredient_classes[ingredient_desc['type']]
            ingredient = ingredient_class(*ingredient_desc['args'], **ingredient_desc['kwargs'])

            ingredients[ingredient_name] = ingredient

        for recipe_order in recipe_orders:
            recipe = Recipe(ingredients=[])
            if target is not None:
                recipe.add(target)
            # loop through the ingredient keys specified by the recipe
            for ingredient_name in recipe_order:
                # get an "initialization request" in the form of a dict
                ingredient = ingredients[ingredient_name]

                # if there is a season to be applied to this ingredient
                seasoning_name = seasoning_links.get(ingredient_name)
                if seasoning_name is not None:
                    # get the ingredient to apply the season
                    seasoning = ingredients[seasoning_name]
                    seasoning.target = target
                    seasoning.season(ingredient)

                # add this created ingredient to the dish recipe for return
                recipe.add(ingredient)

            dish = Dish(recipe=recipe)
            target = dish.serve()

        return target
