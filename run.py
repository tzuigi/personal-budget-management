from app import create_app

# cream aplicatia folosind factory
app = create_app()

if __name__ == '__main__':
    # verificarea incarcarii configurarii: afisam URI-ul bazei de date
    print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
    # pornim serverul in modul debug pentru dezvoltare
    app.run(debug=True)