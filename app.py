# ... (el resto del código igual)

@app.route('/dashboard/editar_proyecto/<int:proyecto_id>', methods=['GET', 'POST'])
@login_required
def editar_proyecto(proyecto_id):
    try:
        proyecto = Proyecto.query.get_or_404(proyecto_id)
        
        if request.method == 'POST':
            try:
                proyecto.name = request.form.get('name')
                proyecto.description = request.form.get('description')
                
                print(f"📝 Editando proyecto: {proyecto.name}")
                
                if 'cover_image' in request.files:
                    file = request.files['cover_image']
                    if file and file.filename != '' and allowed_file(file.filename):
                        # Eliminar imagen anterior si existe
                        if proyecto.cover_image:
                            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], proyecto.cover_image)
                            if os.path.exists(old_image_path):
                                os.remove(old_image_path)
                                print(f"🗑️ Imagen anterior eliminada: {proyecto.cover_image}")
                        
                        # Guardar nueva imagen
                        filename = secure_filename(file.filename)
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        proyecto.cover_image = filename
                        print(f"📸 Nueva imagen guardada: {filename}")
                
                db.session.commit()
                flash('Proyecto actualizado exitosamente!', 'success')
                return redirect(url_for('dashboard_panel'))
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error al actualizar proyecto: {e}")
                flash(f'Error al actualizar proyecto: {str(e)}', 'error')
        
        return render_template('dashboard/editar_proyecto.html', proyecto=proyecto)
        
    except Exception as e:
        print(f"❌ Error cargando página de edición: {e}")
        flash(f'Error cargando el proyecto: {str(e)}', 'error')
        return redirect(url_for('dashboard_panel'))
