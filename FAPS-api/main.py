from fastapi import FastAPI, Depends, Response, status, HTTPException
from typing import Optional
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from schemas import Post
from router import post
from typing import List

import models, schemas
from database import SessionLocal, engine, get_db
from sqlalchemy.orm import Session
from hashing import Hash


###############################################################################
app = FastAPI()


###############################################################################
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]

        # Validate username/password credentials
        # And update session
        request.session.update({"token": "..."})

        return True

    async def logout(self, request: Request) -> bool:
        # Usually you'd want to just clear the session
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Optional[RedirectResponse]:
        token = request.session.get("token")

        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        # Check the token in depth


authentication_backend = AdminAuth(secret_key="12345")
admin = Admin(app=app, engine=engine, authentication_backend=authentication_backend)

# admin = Admin(app, engine)

class UserAdmin(ModelView, model=models.User):
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_list = [models.User.id, models.User.name]

class PostAdmin(ModelView, model=models.Post):
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_list = [models.Post.id, models.Post.title, models.Post.body, models.Post.author_id, models.Post.author]


admin.add_view(UserAdmin)
admin.add_view(PostAdmin)
###############################################################################
@app.get('/')
def index():
    return 'Welcome to FAPS Stack'


app.include_router(post.router)
###############################################################################

@app.post('/blogpost', status_code=status.HTTP_201_CREATED, tags=['posts'])
def create(request: schemas.Post, db: Session = Depends(get_db)):
    new_post = models.Post(title=request.title, body=request.body, author_id=request.author_id)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@app.delete('/blogpost/{post_id}', status_code=200, tags=['posts'])
def destroy(post_id, db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.id == post_id)
    if not post.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found")
    post.delete(synchronize_session=False)
    db.commit()
    return {'detail': f"Post with id {post_id} was deleted"}

@app.put('/blogpost/{id}', status_code=status.HTTP_202_ACCEPTED, tags=['posts'])
def update(id, request: schemas.Post, db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.id == id)
    if not post.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {id} not found")
    post.update({'title': request.title, 'body': request.body})
    db.commit()
    return {'detail': f"Post with id {id} was updated"}

@app.get('/blogposts', response_model=List[schemas.ShowPost], tags=['posts'])
def get_posts(db: Session = Depends(get_db)):
   posts = db.query(models.Post).all()
   return posts

@app.get('/blogpost/{id}', status_code=200, response_model=schemas.ShowPost, tags=['posts'])
def read_post(id, response: Response, db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.id == id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {id} is not available")
    return post

###############################################################################

@app.post('/user', response_model=schemas.ShowUser, tags=['users'])
def create_user(request: schemas.User, db: Session = Depends(get_db)):
    new_user = models.User(name = request.name, email = request.email, password = Hash.bcrypt(request.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get('/users', response_model=List[schemas.ShowUser], tags=['users'])
def get_users(db: Session = Depends(get_db)):
   users = db.query(models.User).all()
   return users

@app.get('/user/{id}', response_model=schemas.ShowUser, tags=['users'])
def get_user(id:int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {id} is not available")
    return user

###############################################################################


