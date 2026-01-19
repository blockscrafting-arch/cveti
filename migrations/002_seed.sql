-- Наполнение тестовыми данными (Seed)

-- Услуги
INSERT INTO services (title, description, price, category, image_url) VALUES
('Комплексная чистка лица', 'Ультразвуковая + механическая чистка, маска по типу кожи', 3500, 'face', 'https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
('Биоревитализация', 'Глубокое увлажнение кожи гиалуроновой кислотой', 5500, 'injection', 'https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
('Массаж лица (45 мин)', 'Лимфодренажный массаж для снятия отеков и лифтинга', 2000, 'massage', 'https://images.unsplash.com/photo-1512290923902-8a9f81dc236c?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'),
('Пилинг PRX-T33', 'Всесезонный пилинг с эффектом биоревитализации', 4000, 'peeling', 'https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60');

-- Мастера
INSERT INTO masters (name, specialization, photo_url) VALUES
('Анна Смирнова', 'Врач-косметолог, дерматолог', 'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=60'),
('Елена Иванова', 'Косметолог-эстетист', 'https://images.unsplash.com/photo-1594824476967-48c8b964273f?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=60');

-- Акции
INSERT INTO promotions (title, description, end_date, image_url) VALUES
('Скидка 20% на первый визит', 'Познакомьтесь с нашей студией выгодно!', '2026-12-31', NULL),
('Курс массажа: 5 сеансов -10%', 'При единовременной оплате курса массажа', '2026-06-01', NULL);
