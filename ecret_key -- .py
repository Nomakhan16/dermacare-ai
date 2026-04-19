[35mapp.py[m[36m:[m[32m174[m[36m:[m        [1;31mpassword[m = request.form.get('[1;31mpassword[m')
[35mapp.py[m[36m:[m[32m185[m[36m:[m        if user and user['[1;31mpassword[m'] == [1;31mpassword[m:
[35mapp.py[m[36m:[m[32m196[m[36m:[m            return render_template('login.html', error='Invalid email or [1;31mpassword[m', 
[35mapp.py[m[36m:[m[32m215[m[36m:[m        [1;31mpassword[m = request.form.get('[1;31mpassword[m')
[35mapp.py[m[36m:[m[32m216[m[36m:[m        confirm_[1;31mpassword[m = request.form.get('confirm_[1;31mpassword[m')
[35mapp.py[m[36m:[m[32m218[m[36m:[m        if not name or not email or not [1;31mpassword[m:
[35mapp.py[m[36m:[m[32m225[m[36m:[m        if len([1;31mpassword[m) < 6:
[35mapp.py[m[36m:[m[32m228[m[36m:[m        if [1;31mpassword[m != confirm_[1;31mpassword[m:
[35mapp.py[m[36m:[m[32m234[m[36m:[m        db.create_user(email, name, [1;31mpassword[m)
[35mapp.py[m[36m:[m[32m698[m[36m:[m@app.route('/forgot-[1;31mpassword[m', methods=['GET', 'POST'])
[35mapp.py[m[36m:[m[32m699[m[36m:[mdef forgot_[1;31mpassword[m():
[35mapp.py[m[36m:[m[32m704[m[36m:[m            return render_template('forgot-[1;31mpassword[m.html', email=email, [1;31mpassword[m=user['[1;31mpassword[m'], found=True)
[35mapp.py[m[36m:[m[32m706[m[36m:[m            return render_template('forgot-[1;31mpassword[m.html', error='Email not found', found=False)
[35mapp.py[m[36m:[m[32m707[m[36m:[m    return render_template('forgot-[1;31mpassword[m.html', found=None)
[35mdatabase.py[m[36m:[m[32m19[m[36m:[m    def create_user(self, email, name, [1;31mpassword[m, skin_type='Normal', hair_type='Normal'):
[35mdatabase.py[m[36m:[m[32m23[m[36m:[m            '[1;31mpassword[m': [1;31mpassword[m,
