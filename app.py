
import os

import nltk.data
from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from googletrans import Translator


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///english.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class TextObject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    text = db.Column(db.Text)
    count_sentences = db.Column(db.Integer)
    count_translated_sentences = db.Column(db.Integer)
    status = db.Column(db.String(32))

class TextForTranslate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_of_text = db.Column(db.Integer)
    sentence_for_translate = db.Column(db.String(512))
    sentence_translated = db.Column(db.String(512))
    sentence_translated_by_user = db.Column(db.String(512), default=None)

class Results(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texts = db.Column(db.Integer)
    texts_finished = db.Column(db.Integer)
    points = db.Column(db.Integer)
    level = db.Column(db.Integer)

@app.route("/")
def main():
    data = {
        "texts": TextObject.query.filter_by(status="New").order_by(TextObject.id.desc()).all(),
        "texts_finished": TextObject.query.filter_by(status="Finished").order_by(TextObject.id.desc()).all()
    }
    return render_template("main.html", **data)

@app.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "GET":
        return render_template("new.html")
    
    if request.method == "POST":
        title, text = request.form["title"], request.form["text"]
        
        tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
        sentences = []
        for i in tokenizer.tokenize(text):
            sentences.append(i)

        text_object = TextObject(
            title=title,
            text=text,
            count_sentences=len(sentences),
            count_translated_sentences=0,
            status="New"
        )
        db.session.add(text_object)
        db.session.commit()
        
        for sentence in sentences:
            db.session.add(TextForTranslate(
                id_of_text=text_object.id,
                sentence_for_translate=sentence,
                sentence_translated=translator.translate(text=sentence, dest="en", src="auto").text
            ))
            db.session.commit()

        results = Results.query.first()
        results.texts += 1

        results.points += 25

        if results.points >= 500:
            results.points -= 500
            results.level += 1

        db.session.commit()
        
        return redirect("/")

@app.route("/text/<int:id>")
def text(id):
    data = {
        "text": TextObject.query.filter_by(id=id).first()
    }
    return render_template("text.html", **data)

@app.route("/text/<int:id>/translate", methods=["GET", "POST"])
def translate(id):
    if request.method == "GET":
        try:
            text = [i for i in TextForTranslate.query.filter_by(id_of_text=id).all() if not i.sentence_translated_by_user][0]
        except:
            text = None

        data = {
            "text": text,
            "form": True
        }
        return render_template("translate.html", **data)

    if request.method == "POST":
        id_, text_ = request.form["id"], request.form["text"]
        text = TextForTranslate.query.filter_by(id=id_).first()

        if text_:
            
            text.sentence_translated_by_user = text_.strip()

            results = Results.query.first()
            results.points += 1

            text_object = TextObject.query.filter_by(id=text.id_of_text).first()
            text_object.count_translated_sentences += 1

            if text_object.count_sentences == text_object.count_translated_sentences:
                text_object.status = "Finished"
                results.texts_finished += 1
                results.points += 50

            if results.points >= 500:
                results.points -= 500
                results.level += 1

            db.session.commit()

        data = {
            "text": text,
            "form": False,
            "id": id
        }
        
        return render_template("translate.html", **data)

@app.route("/text/<int:id>/read")
def read(id):
    data = {
        "text": [i for i in TextForTranslate.query.filter_by(id_of_text=id).all() if i.sentence_translated_by_user]
    }
    return render_template("read.html", **data)

@app.route("/text/<int:id>/remove")
def remove(id):
    text = TextObject.query.filter_by(id=id).first()

    results = Results.query.first()
    results.texts -= 1

    if text.status == "Finished":
        results.texts_finished -= 1

    TextObject.query.filter_by(id=id).delete()

    TextForTranslate.query.filter_by(id_of_text=id).delete()

    db.session.commit()
    return redirect("/")

@app.route("/results")
def results():
    data = {
        "results": Results.query.first()
    }
    return render_template("results.html", **data)


if __name__ == "__main__":
    nltk.download('punkt')
    translator = Translator()
    if not os.path.isfile("instance/english.db"):
        with app.app_context():
            db.create_all()

    app.run(debug=True)
