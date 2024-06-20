from goodwill import Category, SimpleListing

from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, update, and_
from sqlalchemy.orm import declarative_base, Session, relationship, backref
from sqlalchemy.exc import IntegrityError, InterfaceError

# connect with data base
engine = create_engine('sqlite:///goodwill/categories.sqlite', echo=False, pool_size=10, max_overflow=20)
# manage tables 
base = declarative_base()

class DbCategory(base):
    __tablename__ = 'Categories'

    categoryId = Column(Integer, primary_key = True, unique = True)
    categoryName = Column(String, primary_key = True)

    parentId = Column(Integer, nullable = True)
    levelNumber = Column(Integer, default = -1)
    subCount = Column(Integer, default = 0)
    children = Column(String, nullable = True) # CSV list

    def __init__(self, json:dict, children:str):
        self.categoryId = json["categoryId"]
        self.categoryName = json["name"]

        self.levelNumber = json["levelNumber"]
        self.parentId = json["parentId"]
        self.subCount = json["subCount"]
        self.children = children # CSV list of children catagory Ids

    def toCategory(self):
        category = Category(
            self.categoryId,
            self.categoryName,
            self.parentId,
            self.levelNumber,
            self.subCount,
            self.children
        )

        return category

def addCategory(json_data, children):
    with Session(engine) as session:
        try: 
            session.add(DbCategory(json_data, children))
        except IntegrityError as e:#figure out how to catch errors from sqlite3 
            print(e)
        except InterfaceError as e:
            print(e)
        session.commit()

# Creates Database
# base.metadata.create_all(engine)

def getQuery(cat_id:int = None, cat_name: str = None) -> Category | None:
    '''
    Returns category with matching criteria if not found returns None.
    '''
    with Session(engine) as session:
        filters = []

        if cat_id:
            filters.append(getattr(DbCategory, "categoryId") == cat_id,)
        
        if cat_name:
            filters.append(getattr(DbCategory, "categoryName") == cat_name,) 

        query = session.query(DbCategory).filter(and_(*filters)) if filters != () else session.query(DbCategory).all()

    query_response = [entry.toCategory() for entry in query]

    if len(query_response) == 1:
        return query_response[0]

    return query_response


def getAllCategories():
    '''
    Returns a list of all top level categories
    '''
    with Session(engine) as session:
        query = session.query(DbCategory).filter(getattr(DbCategory, "levelNumber") == 1)

    query_response = [entry.toCategory() for entry in query]

    return query_response


def getCategoriesByPar(parentId: int) -> list[Category]:
    with Session(engine) as session:
        query = session.query(DbCategory).filter(getattr(DbCategory, "parentId") == parentId)

    query_response = [entry.toCategory() for entry in query]

    return query_response


def hasChildren(categoryId: int):
    with Session(engine) as session:
        query = session.query(DbCategory).filter(getattr(DbCategory, "categoryId") == categoryId)

    response = [entry.toCategory() for entry in query]

    if response[0].children != None:
        return True

    else:
        return False


# ADD QUERY FUNCTION TO CATEGORY CLASS
def getParentCat(self: Category):
    '''
    Returns list of all parent categories
    '''
    if self.parentId == -1:
        return None
        
    par_cat = getQuery(cat_id = self.parentId)
    
    if par_cat.parentId != -1:
        return (getQuery(cat_id = par_cat.parentId), par_cat)
    
    return par_cat

setattr(Category, 'getParentCat', getParentCat)


# ADD FUNCTION TO GET ALL IDS
def getCategoryIds(self: Category):
    '''
    Returns a str containing all category ids for api request\n
    Ex. -1,456,789 (-1 will be in place of None)
    '''
    if self.parentId == -1:
        return f"-1,-1,{self.categoryId}" #TODO double check that this is what is done 
    
    par_ids : Category | tuple[Category] = self.getParentCat()

    if type(par_ids) == tuple:
        return f"{par_ids[0].categoryId},{par_ids[1].categoryId},{self.categoryId}"
    
    return f"-1,{par_ids.categoryId},{self.categoryId}"

setattr(Category, 'getCategoryIds', getCategoryIds)


# ADD FUNCTION TO GET ALL CHILDREN
def getChildren(self: Category):
    '''
    Returns a tuple containing all child categories or None if the Category has none
    '''
    if not self.children:
        return None
    
    categories = getCategoriesByPar(self.categoryId)

    return categories

setattr(Category, 'getChildren', getChildren)

@staticmethod
def getCategoryName(data: dict):
    categoryName = data.get(
        "categoryName", 
        getQuery(cat_id = data["categoryId"]).categoryName
    )

    return categoryName

setattr(SimpleListing, 'getCategoryName', getCategoryName)