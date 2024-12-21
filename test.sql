CREATE DATABASE IF NOT EXISTS `LOGIN` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `LOGIN`;

CREATE TABLE IF NOT EXISTS `form` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `username` varchar(50) NOT NULL,
    `password` varchar(255) NOT NULL,
    `isAdmin` boolean NOT NULL,
    `registration_date` varchar(25) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


CREATE TABLE IF NOT EXISTS `questions` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `qid` varchar(50) not null UNIQUE,
    `question` varchar(250) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;
 insert into `questions` (`qid`, `question`) values
 (-3, "Рекомендовано внесудебное банкротство"),
 (-2, "Рекомендовано судебное банкротство"),
 (-1, "Банкротство для Вас невозможно"),
 (1,  "Проходили ли Вы процедуру банкротства?"),
 (2, "Прошло уже более 5 лет с момента прохождения процедуры банкротства?"),
 (3, "Ваша общая сумма долговых обязательств менее 500 тысяч рублей?"),
 (4, "Ваша общая сумма долговых обязательств менее 25 тысяч рублей?"),
 (5, "Ваша общая сумма долговых обязательств более 1 миллиона рублей?"),
 (6, "Действует ли в отношении Вас неоконченное исполнительное производство по взысканию денежных средств?"),
 (7, "Исполнительный документ был выдан Вам 7 или менее лет назад?"),
 (8, "Действовало ли ранее в отношении Вас исполнительное производство по взысканию денежных средств?"),
 (9, "Действует ли в отношении Вас неоконченное исполнительное производство по взысканию денежных средств?"),
 (10, "Ваш основной доход это заработная плата или доходы с ИП или Вы безработный?"),
 (11, "Получаете ли Вы пенсию или социальные выплаты?"),
 (12, "Предъявлялся ли Вам не позднее 1 года назад исполнительный документ по имущественным требованиям, который не был исполнен или был исполнен частично?"),
 (13, "Есть ли у Вас имущество, на которое можно обратить взыскание?"),
 (14, "Срок просрочки Ваших обязательств уже наступил?"),
 (15, "Срок просрочки Ваших обязательств более 3 месяцев?"),
 (16, "Срок с момента выявления у Вас неплатежеспособности и (или) недостаточности денежных средств более 30 дней?"),
 (17, "Являетесь ли Вы неплатежеспособным?"),
 (18, "Достаточно ли у Вас имущества для исполнения обязательств?"),
 (19, "Есть ли у Вас документальное подтверждение неплатежеспособности?"),
 (20, "Есть ли у Вас непогашенная судимость за экономические преступления?");
 
 create table if not exists `answers` (
	`aid` varchar(50) not null primary key,
    `text` varchar(250) not null
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

 insert into `answers` (`aid`, `text`) values 
 ('yes', 'Да'),
 ('no', 'Нет'),
 ('end', 'Производство окончено в связи с отсутствием имущества'),
 ('again','	Производство окончено, но после этого возбуждено новое');

CREATE TABLE IF NOT EXISTS `sessions` (
    `uid` varchar(50) NOT NULL,
    `session` int(11) UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `result` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `session` int(11) not null,
    `uid` varchar(50) NOT NULL,
    `qid` varchar(50) NOT NULL,
    `answer` varchar(25),
    `date` VARCHAR(25),
    PRIMARY KEY (`id`),
    FOREIGN KEY (`qid`) REFERENCES questions (`qid`)

) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;


INSERT INTO `form` (`username`, `password`, `isAdmin`, `registration_date`) 
VALUES 
('admin@gmail.com', '6b86b273ff34fce19d6b804eff5a3f5', true, '2024-11-21 10:15:30'),
('user1@gmail.com', 'e99a18c428cb38d5f260853678922e03', false, '2024-11-22 14:25:45'),
('user2@gmail.com', 'ab56b4d92b40713acc5af89985d4b786', false, '2024-11-23 09:35:50'),
('user3@gmail.com', '4e07408562bedb8b60ce05c1decfe3ad', false, '2024-11-24 16:45:55'),
('user4@gmail.com', 'e4da3b7fbbce2345d7772b0674a318d5', false, '2024-11-25 11:55:00'),
('user5@gmail.com', '1679091c5a880faf6fb5e6087eb1b2dc', false, '2024-11-26 13:05:05'),
('user6@gmail.com', '8f14e45fceea167a5a36dedd4bea2543', true, '2024-11-27 15:15:10'),
('user7@gmail.com', 'c9f0f895fb98ab9159f51fd0297e236d', false, '2024-11-28 17:25:15'),
('user8@gmail.com', '45c48cce2e2d7fbdea1afc51c7c6ad26', true, '2024-11-29 19:35:20'),
('user9@gmail.com', 'd3d9446802a44259755d38e6d163e820', false, '2024-11-30 21:45:25'),
('user10@gmail.com', '6512bd43d9caa6e02c990b0a82652dca', false, '2024-11-21 08:55:30'),
('user11@gmail.com', 'c20ad4d76fe97759aa27a0c99bff6710', false, '2024-11-22 10:05:35'),
('user12@gmail.com', 'c51ce410c124a10e0db5e4b97fc2af39', false, '2024-11-23 12:15:40'),
('user13@gmail.com', 'aab3238922bcc25a6f606eb525ffdc56', true, '2024-11-24 14:25:45'),
('user14@gmail.com', '9bf31c7ff062936a96d3c8bd1f8f2ff3', false, '2024-11-25 16:35:50'),
('user15@gmail.com', 'c74d97b01eae257e44aa9d5bade97baf', false, '2024-11-26 18:45:55'),
('user16@gmail.com', '70efdf2ec9b086079795c442636b55fb', false, '2024-11-27 20:55:00'),
('user17@gmail.com', '6f4922f45568161a8cdf4ad2299f6d23', false, '2024-11-28 22:05:05'),
('user18@gmail.com', '1f0e3dad99908345f7439f8ffabdffc4', false, '2024-11-29 23:15:10'),
('user19@gmail.com', '98f13708210194c475687be6106a3b84', false, '2024-11-30 09:25:15'),
('user20@gmail.com', '3c59dc048e8850243be8079a5c74d079', false, '2024-11-21 11:35:20');