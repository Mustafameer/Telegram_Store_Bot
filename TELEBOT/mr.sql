-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Jan 12, 2026 at 04:21 PM
-- Server version: 8.0.37-0ubuntu0.22.04.3
-- PHP Version: 7.4.33

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `mr`
--

-- --------------------------------------------------------

--
-- Table structure for table `bot`
--

CREATE TABLE `bot` (
  `key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `value` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `bot`
--

INSERT INTO `bot` (`key`, `value`) VALUES
('admins', '[5420647695]'),
('owners', '[787700246,204378180]'),
('profit', '{\"asiacell\":0,\"zain\":0,\"korek\":0,\"iraqsell\":0,\"alkafil\":0,\"creditrequest\":0,\"others\":0,\"netzain\":0,\"netasiacell\":0}'),
('status', '{\"ok\":true}'),
('step', '{\"Group\":\"14136917008923842\"}');

-- --------------------------------------------------------

--
-- Table structure for table `photos`
--

CREATE TABLE `photos` (
  `company` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `1` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `2` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `3` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `5` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `10` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `15` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `20` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `25` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `30` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `35` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `40` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `50` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `60` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `100` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `250` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `500` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `photos`
--

INSERT INTO `photos` (`company`, `1`, `2`, `3`, `5`, `10`, `15`, `20`, `25`, `30`, `35`, `40`, `50`, `60`, `100`, `250`, `500`) VALUES
('alkafil', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]\r\n', '[]', '[]', '[]', '[]', '[]', '[]'),
('asiacell', '[]', '[]', '[]', '[\"AgACAgIAAxkBAAECEedpVAJmzDUaHb56NVRgr94MLmz4WAACRQ5rG7TZoEoNdJVmJTNDHAEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEehpVAJmESuWAwIJPOUn9csqfuxMjgACRg5rG7TZoEr-wghT-ICsZgEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEelpVAJmAbO0YJgJEXYTAVny0GVNPgACRw5rG7TZoEq6u0_iRkCeCQEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEeppVAJm381hOA_v-WsMjgLXQ0D_NwACSA5rG7TZoEpYSi4lTbNKvwEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEj5pVWLILRUoUm8IDoQf7c1szdS-3gACrRNrG7TZqEotMYlINOrQKAEAAwIAA3kAAzgE\"]', '[\"AgACAgIAAxkBAAECEfNpVALn4FYPdw0PYH3FHNY5VlfpAwACVQ5rG7TZoEqJjiliciTxIQEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEfRpVALnVrHMGdXEL2vwA16lv5876QACVg5rG7TZoEqErsvzTZgDxAEAAwIAA3kAAzgE\"]', '[]', '[]', '[]', '[]', '[]\r\n', '[]', '[]', '[]', '[]', '[]', '[]'),
('iraqsell', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]\r\n', '[]', '[]', '[]', '[]', '[]', '[]'),
('korek', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]\r\n', '[]', '[]', '[]', '[]', '[]', '[]'),
('others', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]\r\n', '[]', '[]', '[]', '[]', '[]', '[]'),
('zain', '[]', '[\"AgACAgIAAxkBAAECDyZpN-yrWe2esVoelP556ITz3KAXkQACbw5rG3jswUlV-1KHTlFP2wEAAwIAA3kAAzYE\",\"AgACAgIAAxkBAAECDydpN-yrLS2eHYUl2oEH-VHk2I_eRAACcA5rG3jswUnx85HhGXroWgEAAwIAA3kAAzYE\"]', '[]', '[\"AgACAgIAAxkBAAECEftpVANm2VU4gjc8Ia8G0FPB2J0KxAACXA5rG7TZoEpCLFOLjWQEsgEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEfxpVANmwJpFa3mXsGBD3M284eNW5AACXQ5rG7TZoEpRrG91kN7hJgEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhFpVAbGiU27eZHkH83yf2xxnpByLgACjQ5rG7TZoEqbagn1B-94FwEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhJpVAbG4XoEBcgnhlQCLvFX1NyDDwACjg5rG7TZoEoYdVD5HWCt5AEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhNpVAbGzsrcxHrNet31FSFNBnIOgAACjw5rG7TZoErgqIg530fomgEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhRpVAbGUp7Vrf6PEh7sRh4KOCvYRAACkA5rG7TZoEq2WAxuemAhXQEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhVpVAbGBOYdFl0Di7GehEDSYgurmAACkQ5rG7TZoEoeVL0VDw4mPgEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhZpVAbGBx1mnmMa34XmaZyBjBIFzAACkg5rG7TZoEr1nSLIy6Q9SgEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhdpVAbGlGIrVw8Oq3kDDWl1xsqOPgACkw5rG7TZoErA0wUPCN0DYgEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhhpVAbGk6JL3xCsHTw21tEVARsgoQAClA5rG7TZoEoqU0hafvhrjAEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhlpVAbGsWtUZ_F6lq9unh43d77LLAAClQ5rG7TZoEp3mGhuM4UYDQEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhppVAbGmnt9gKP3ArdQC6B-lCreCwAClg5rG7TZoErbPsWbYEt0mwEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEhxpVAbHq9AFha7duZp3aFXOQby0rgAClw5rG7TZoEr0N4-Eyy9kugEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEh1pVAbH4Waz4mXJTqFTg-cRDgzakQACmA5rG7TZoEoPobGlE0DGEQEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEh5pVAbHB5ccbhFDfRpYTRvuJhAh5AACmQ5rG7TZoErU6qfwcrS5FAEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEh9pVAbHy_jjPX7qx53e-49qNQ25ZgACmg5rG7TZoEojaipDm2bWpgEAAwIAA3kAAzgE\"]', '[\"AgACAgIAAxkBAAECEgABaVQDlQoPDhjmB2CQiwaW-EZvkxkAAmEOaxu02aBKRNu8FgrTSSABAAMCAAN5AAM4BA\",\"AgACAgIAAxkBAAECEiFpVAeC3Uq6010-lnFOGsKvRZKyMAACoQ5rG7TZoEpuWDzcuzQs7AEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEiJpVAeCUr7BsZDWBNhYX-WRl0XBaQACog5rG7TZoEqFG50_F_-ntAEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEiNpVAeCdGWwadEFnWzUV0B_lbj-IgACow5rG7TZoEox5JqSgcaUrgEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEiRpVAeCmz1SJGcD1qqbeKKutx3ixAACpA5rG7TZoEpoF9CuNwiLgwEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEiVpVAeCKxrBIMDEW7_OseWoT2wO-QACpQ5rG7TZoEo76IToNYHBqwEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEiZpVAeCUeijbJeD8ezxBsY8prJoGQACpg5rG7TZoEq9MiIiagxKXAEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEidpVAeCsoHDcnokYsr6auHhJJD72wACpw5rG7TZoEqsCB5gm68THQEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEihpVAeCpzlNa7d4uT8qqlk2Ph4dvwACqA5rG7TZoEq-8XWhEDxGyAEAAwIAA3kAAzgE\",\"AgACAgIAAxkBAAECEilpVAeCnsErYgABrWjmcw3QwxouiD8AAqkOaxu02aBKImkuRG_28ZYBAAMCAAN5AAM4BA\",\"AgACAgIAAxkBAAECEippVAeCM4y5JD-UCXTtbzEw5wzLpQACqg5rG7TZoErJSeZDXJx_TwEAAwIAA3kAAzgE\"]', '[]', '[]', '[]', '[]', '[]\r\n', '[]', '[]', '[]', '[]', '[]', '[]');

-- --------------------------------------------------------

--
-- Table structure for table `priceslater`
--

CREATE TABLE `priceslater` (
  `id` int NOT NULL,
  `company` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `select` int NOT NULL,
  `1` int NOT NULL,
  `2` int NOT NULL,
  `3` int NOT NULL,
  `5` int NOT NULL,
  `10` int NOT NULL,
  `15` int NOT NULL,
  `20` int NOT NULL,
  `25` int NOT NULL,
  `30` int NOT NULL,
  `35` int NOT NULL,
  `40` int NOT NULL,
  `50` int NOT NULL,
  `60` int NOT NULL,
  `100` int NOT NULL,
  `250` int NOT NULL,
  `500` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `priceslater`
--

INSERT INTO `priceslater` (`id`, `company`, `type`, `select`, `1`, `2`, `3`, `5`, `10`, `15`, `20`, `25`, `30`, `35`, `40`, `50`, `60`, `100`, `250`, `500`) VALUES
(1, 'asiacell', 'transfer', 1, 0, 3000, 0, 5750, 11000, 16500, 26000, 27000, 32000, 44000, 52000, 55000, 65000, 107500, 0, 0),
(2, 'asiacell_Before', 'transfer', 1, 0, 2050, 0, 5000, 10000, 15000, 24000, 25000, 30000, 38000, 48000, 52500, 65000, 120000, 0, 0),
(3, 'zain', 'transfer', 1, 0, 3500, 0, 6000, 11000, 16000, 21500, 26500, 31500, 36500, 42000, 52000, 0, 103000, 0, 0),
(4, 'zain_Before', 'transfer', 1, 0, 2050, 0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 50000, 0, 100000, 0, 0),
(5, 'korek', 'transfer', 1, 0, 0, 0, 6000, 12000, 18000, 24000, 30000, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(6, 'korek_Before', 'transfer', 1, 0, 0, 0, 6250, 12250, 18000, 24000, 30000, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(7, 'iraqsell', 'transfer', 1, 0, 0, 3000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(8, 'iraqsell_Before', 'transfer', 1, 0, 0, 3450, 5750, 11500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(9, 'alkafil', 'transfer', 1, 0, 0, 3000, 7000, 13500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(10, 'alkafil_Before', 'transfer', 1, 0, 0, 3450, 5750, 11500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(11, 'creditrequest', 'transfer', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100000, 250000, 500000),
(12, 'creditrequest_Before', 'transfer', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100000, 250000, 500000),
(13, 'asiacell', 'transfer', 2, 0, 2750, 0, 5350, 11000, 15750, 25000, 26500, 31000, 0, 42000, 52500, 62000, 105000, 0, 0),
(14, 'asiacell_Before', 'transfer', 2, 0, 2060, 0, 5000, 10000, 15000, 24000, 25000, 30000, 0, 42000, 52500, 0, 120000, 0, 0),
(15, 'zain', 'transfer', 2, 0, 2750, 0, 5750, 10750, 15750, 21000, 26500, 31000, 36000, 41500, 52000, 0, 102000, 0, 0),
(16, 'zain_Before', 'transfer', 2, 0, 2050, 0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 50000, 0, 100000, 0, 0),
(17, 'korek', 'transfer', 2, 0, 0, 0, 6000, 12000, 15000, 20000, 25000, 30000, 0, 40000, 50000, 0, 100000, 0, 0),
(18, 'korek_Before', 'transfer', 2, 0, 0, 0, 5900, 11850, 18000, 24000, 30000, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(19, 'iraqsell', 'transfer', 2, 0, 0, 3750, 5625, 11250, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(20, 'iraqsell_Before', 'transfer', 2, 0, 0, 3350, 5350, 10350, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(21, 'alkafil', 'transfer', 2, 0, 0, 3500, 6750, 12750, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(22, 'alkafil_Before', 'transfer', 2, 0, 0, 3450, 5750, 11500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(23, 'creditrequest', 'transfer', 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100000, 250000, 500000),
(24, 'creditrequest_Before', 'transfer', 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100000, 250000, 500000),
(25, 'asiacell', 'photos', 1, 0, 3000, 0, 6000, 11000, 16250, 21500, 26500, 31500, 0, 41500, 61000, 0, 122000, 0, 0),
(26, 'asiacell_Before', 'photos', 1, 0, 2675, 0, 5000, 10000, 15000, 20000, 25000, 30000, 0, 40000, 60000, 0, 120000, 0, 0),
(27, 'zain', 'photos', 1, 0, 3000, 0, 6000, 11000, 16250, 28000, 35000, 42000, 49000, 56000, 70000, 0, 120000, 0, 0),
(28, 'zain_Before', 'photos', 1, 0, 2700, 0, 5100, 10150, 18190, 24500, 30500, 36300, 42500, 48000, 60000, 0, 120000, 0, 0),
(29, 'korek', 'photos', 1, 0, 0, 0, 6500, 12500, 18000, 24000, 30000, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(30, 'korek_Before', 'photos', 1, 0, 0, 0, 5850, 11950, 18000, 24000, 30000, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(31, 'iraqsell', 'photos', 1, 0, 0, 3500, 6500, 12500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(32, 'iraqsell_Before', 'photos', 1, 0, 0, 3000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(33, 'alkafil', 'photos', 1, 0, 0, 3500, 6500, 13500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(34, 'alkafil_Before', 'photos', 1, 0, 0, 3000, 5975, 11975, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(35, 'others', 'photos', 1, 10, 10, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(36, 'others_Before', 'photos', 1, 100, 100, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(37, 'asiacell', 'photos', 2, 0, 2750, 0, 5750, 10750, 15750, 21000, 26000, 31000, 0, 41000, 60000, 0, 120000, 0, 0),
(38, 'asiacell_Before', 'photos', 2, 0, 2650, 0, 5000, 10000, 15000, 20000, 25000, 30000, 0, 40000, 59600, 0, 119400, 0, 0),
(39, 'zain', 'photos', 2, 0, 3000, 0, 5750, 10750, 15750, 26000, 34000, 40000, 46000, 54000, 66000, 0, 120000, 0, 0),
(40, 'zain_Before', 'photos', 2, 0, 2600, 0, 5100, 10150, 18190, 23550, 30300, 36300, 42500, 47500, 59500, 0, 118000, 0, 0),
(41, 'korek', 'photos', 2, 0, 0, 0, 6000, 12000, 18000, 24000, 30000, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(42, 'korek_Before', 'photos', 2, 0, 0, 0, 5850, 11850, 17250, 23500, 29400, 35400, 0, 47250, 59500, 0, 119000, 0, 0),
(43, 'iraqsell', 'photos', 2, 0, 0, 3500, 6000, 12000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(44, 'iraqsell_Before', 'photos', 2, 0, 0, 3000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(45, 'alkafil', 'photos', 2, 0, 0, 3500, 6250, 13000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(46, 'alkafil_Before', 'photos', 2, 0, 0, 3450, 6075, 11975, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(47, 'others', 'photos', 2, 1250, 18500, 8000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(48, 'others_Before', 'photos', 2, 1225, 18150, 8000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(49, 'netzain', 'transfer', 1, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(50, 'netzain_Before', 'transfer', 1, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(51, 'netzain', 'transfer', 2, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(52, 'netzain_Before', 'transfer', 2, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(53, 'netasiacell', 'transfer', 1, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(54, 'netasiacell_Before', 'transfer', 1, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(55, 'netasiacell', 'transfer', 2, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(56, 'netasiacell_Before', 'transfer', 2, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);

-- --------------------------------------------------------

--
-- Table structure for table `pricesnow`
--

CREATE TABLE `pricesnow` (
  `id` int NOT NULL,
  `company` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `select` int NOT NULL,
  `1` int NOT NULL,
  `2` int NOT NULL,
  `3` int NOT NULL,
  `5` int NOT NULL,
  `10` int NOT NULL,
  `15` int NOT NULL,
  `20` int NOT NULL,
  `25` int NOT NULL,
  `30` int NOT NULL,
  `35` int NOT NULL,
  `40` int NOT NULL,
  `50` int NOT NULL,
  `60` int NOT NULL,
  `100` int NOT NULL,
  `250` int NOT NULL,
  `500` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `pricesnow`
--

INSERT INTO `pricesnow` (`id`, `company`, `type`, `select`, `1`, `2`, `3`, `5`, `10`, `15`, `20`, `25`, `30`, `35`, `40`, `50`, `60`, `100`, `250`, `500`) VALUES
(1, 'asiacell', 'transfer', 1, 0, 3000, 0, 5500, 10600, 15600, 21000, 26000, 31250, 0, 41500, 51500, 62000, 103000, 0, 0),
(2, 'asiacell_Before', 'transfer', 1, 0, 2160, 0, 5400, 10800, 16200, 21600, 27000, 32400, 0, 43200, 54000, 64800, 108000, 0, 0),
(3, 'zain', 'transfer', 1, 0, 3000, 0, 5500, 10600, 15650, 21500, 26000, 31500, 36000, 41500, 52000, 0, 103000, 0, 0),
(4, 'zain_Before', 'transfer', 1, 0, 2240, 0, 5000, 10000, 16800, 20200, 25000, 30000, 35000, 40000, 50000, 0, 100000, 0, 0),
(5, 'korek', 'transfer', 1, 0, 0, 0, 0, 0, 16500, 24000, 0, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(6, 'korek_Before', 'transfer', 1, 0, 0, 0, 6250, 12250, 18000, 24000, 30000, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(7, 'iraqsell', 'transfer', 1, 0, 0, 0, 5500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(8, 'iraqsell_Before', 'transfer', 1, 0, 0, 3450, 5750, 11500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(9, 'alkafil', 'transfer', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(10, 'alkafil_Before', 'transfer', 1, 0, 0, 3450, 5750, 11500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(11, 'creditrequest', 'transfer', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(12, 'creditrequest_Before', 'transfer', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 50000, 0, 100000, 250000, 500000),
(13, 'asiacell', 'transfer', 2, 1650, 2250, 0, 5000, 10000, 15000, 20300, 25000, 30250, 0, 40500, 50750, 60750, 100000, 0, 0),
(14, 'asiacell_Before', 'transfer', 2, 1000, 2160, 0, 5400, 10800, 16200, 21600, 27000, 32400, 0, 43200, 54000, 64800, 108000, 0, 0),
(15, 'zain', 'transfer', 2, 1250, 2500, 0, 5250, 10400, 15500, 20600, 26000, 30700, 35750, 40750, 51000, 0, 101000, 0, 0),
(16, 'zain_Before', 'transfer', 2, 1000, 2240, 0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 50000, 0, 100000, 0, 0),
(17, 'korek', 'transfer', 2, 0, 0, 0, 5750, 12000, 15000, 20000, 0, 30000, 40500, 40000, 50000, 0, 100000, 0, 0),
(18, 'korek_Before', 'transfer', 2, 0, 0, 0, 5500, 11000, 18000, 24000, 30000, 36000, 39000, 48000, 60000, 0, 120000, 0, 0),
(19, 'iraqsell', 'transfer', 2, 1360, 2360, 3360, 4850, 9700, 14550, 19500, 24250, 29100, 34000, 38800, 48500, 58250, 97000, 0, 0),
(20, 'iraqsell_Before', 'transfer', 2, 1360, 2360, 3350, 5250, 10500, 15750, 21000, 26250, 31500, 31500, 42000, 52500, 0, 0, 0, 0),
(21, 'alkafil', 'transfer', 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(22, 'alkafil_Before', 'transfer', 2, 0, 0, 3450, 5750, 11500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(23, 'creditrequest', 'transfer', 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 50000, 0, 100000, 250000, 500000),
(24, 'creditrequest_Before', 'transfer', 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 50000, 0, 100000, 250000, 500000),
(25, 'asiacell', 'photos', 1, 0, 3000, 4000, 5500, 10500, 16500, 0, 26500, 32000, 0, 42500, 52500, 0, 105000, 0, 0),
(26, 'asiacell_Before', 'photos', 1, 0, 2550, 0, 5000, 10000, 15000, 24000, 25000, 30000, 0, 40000, 50000, 0, 102000, 0, 0),
(27, 'zain', 'photos', 1, 0, 3500, 0, 5650, 10650, 16000, 0, 26500, 37000, 43500, 0, 62000, 0, 122500, 0, 0),
(28, 'zain_Before', 'photos', 1, 0, 3050, 0, 5000, 10000, 15000, 24500, 30500, 36500, 42550, 48000, 60600, 0, 121200, 0, 0),
(29, 'korek', 'photos', 1, 1300, 0, 0, 5500, 10500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(30, 'korek_Before', 'photos', 1, 1200, 0, 0, 5875, 10000, 18000, 24000, 30000, 36000, 0, 48000, 60000, 0, 120000, 0, 0),
(31, 'iraqsell', 'photos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(32, 'iraqsell_Before', 'photos', 1, 0, 0, 3000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(33, 'alkafil', 'photos', 1, 0, 0, 0, 6500, 12500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(34, 'alkafil_Before', 'photos', 1, 0, 0, 3000, 6075, 12075, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(35, 'others', 'photos', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(36, 'others_Before', 'photos', 1, 100, 100, 3650, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(37, 'asiacell', 'photos', 2, 1350, 2550, 3600, 5250, 10350, 16000, 0, 26500, 30750, 0, 42500, 52000, 0, 103500, 0, 0),
(38, 'asiacell_Before', 'photos', 2, 1350, 2250, 3075, 5000, 10000, 15000, 23500, 25000, 30000, 0, 40000, 50000, 0, 102000, 0, 0),
(39, 'zain', 'photos', 2, 0, 2750, 0, 5250, 10400, 16000, 0, 26500, 36700, 43000, 0, 61000, 0, 122000, 0, 0),
(40, 'zain_Before', 'photos', 2, 0, 3050, 0, 5000, 10000, 15200, 23550, 30400, 36500, 42875, 47500, 60600, 0, 121200, 0, 0),
(41, 'korek', 'photos', 2, 1300, 0, 0, 5250, 10250, 15000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(42, 'korek_Before', 'photos', 2, 1200, 0, 0, 5025, 11950, 15000, 23500, 29400, 35400, 0, 47250, 59500, 0, 119000, 0, 0),
(43, 'iraqsell', 'photos', 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(44, 'iraqsell_Before', 'photos', 2, 0, 0, 3000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(45, 'alkafil', 'photos', 2, 0, 0, 0, 6250, 12300, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(46, 'alkafil_Before', 'photos', 2, 0, 0, 0, 6075, 12075, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(47, 'others', 'photos', 2, 1250, 0, 3650, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(48, 'others_Before', 'photos', 2, 1225, 18150, 3650, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(49, 'netzain', 'transfer', 1, 0, 7000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(50, 'netzain_Before', 'transfer', 1, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(51, 'netzain', 'transfer', 2, 0, 7000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(52, 'netzain_Before', 'transfer', 2, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(53, 'netasiacell', 'transfer', 1, 0, 0, 0, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(54, 'netasiacell_Before', 'transfer', 1, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(55, 'netasiacell', 'transfer', 2, 0, 0, 0, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(56, 'netasiacell_Before', 'transfer', 2, 1000, 7000, 30000, 5000, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);

-- --------------------------------------------------------

--
-- Table structure for table `request`
--

CREATE TABLE `request` (
  `id` int NOT NULL,
  `ts` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `company` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `number` int NOT NULL,
  `nol` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `req_number` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `from_id` bigint NOT NULL,
  `message_id` int NOT NULL,
  `message_id_req` int NOT NULL,
  `message_id_cancel` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `request`
--

INSERT INTO `request` (`id`, `ts`, `company`, `number`, `nol`, `req_number`, `from_id`, `message_id`, `message_id_req`, `message_id_cancel`) VALUES
(138, 'transfer', 'alkafil', 10, 'L', '07601017300', 450878722, 45129, 45130, 0),
(230, 'transfer', 'creditrequest', 50, 'N', '00000', 1054084412, 46486, 46487, 0),
(522, 'transfer', 'creditrequest', 50, 'N', '00000000', 1054084412, 52258, 52259, 0),
(577, 'transfer', 'asiacell', 5, 'N', '+964 770 007 7331', 204378180, 59587, 59588, 0),
(590, 'transfer', 'zain', 15, 'L', '07832438384', 231713734, 59670, 59671, 59724),
(717, 'transfer', 'iraqsell', 5, 'N', '07719882565', 1388129818, 66152, 66153, 0),
(793, 'transfer', 'zain', 5, 'L', '0780 599 2495', 40474770, 66925, 66926, 0),
(888, 'transfer', 'asiacell', 5, 'N', '07724418969', 900319241, 67577, 67578, 0),
(934, 'transfer', 'zain', 10, 'N', '07805988500', 900319241, 73210, 73211, 0),
(1108, 'transfer', 'korek', 5, 'N', '07500723273', 1513449509, 75219, 75220, 0),
(1166, 'transfer', 'zain', 10, 'N', '0780 274 7603', 1513449509, 0, 0, 85389),
(1218, 'transfer', 'asiacell', 15, 'N', '07757158849', 5360262351, 119972, 119973, 119974);

-- --------------------------------------------------------

--
-- Table structure for table `states`
--

CREATE TABLE `states` (
  `id` int NOT NULL,
  `state` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `param` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int NOT NULL,
  `status` int NOT NULL,
  `from_id` bigint NOT NULL,
  `select` int NOT NULL,
  `money` int NOT NULL,
  `allmoney` int NOT NULL,
  `limit` int NOT NULL,
  `report` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `status`, `from_id`, `select`, `money`, `allmoney`, `limit`, `report`) VALUES
(14, 1, 109069557, 2, 279350, 11401650, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(15, 1, 606795627, 2, 47715, 2662115, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(16, 1, 1083996028, 1, -9350, 953150, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(17, 1, 838653668, 2, -3225, 8955575, 100, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(20, 1, 231713734, 1, 150, 4212900, 250000, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(22, 1, 450878722, 1, 58500, 230000, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(23, 1, 1355021070, 2, -10000, 3497750, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(24, 1, 1075076667, 1, -2800, 2050900, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(25, 1, 396923888, 1, 114750, 0, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(26, 1, 135898850, 1, -2000, 903500, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(28, 1, 93423863, 2, 5750, 5750, 53250, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(29, 1, 40474770, 2, -100, 14406875, 750000, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(30, 1, 402182707, 2, -10600, 1184400, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(31, 1, 1289131892, 2, 85800, 326800, 250000, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(32, 1, 900319241, 2, -1325, 2474475, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(34, 1, 243910660, 2, -80530, 13199920, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(36, 1, 986765668, 1, 29550, 1498550, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(37, 1, 1452715506, 1, 365750, 2225800, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(39, 1, 1344957103, 1, -3650, 1638350, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(41, 1, 1513449509, 2, -2090, 796410, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(45, 1, 1428000116, 2, -4225, 745775, 100, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(46, 1, 675171446, 1, 22200, 634700, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(51, 1, 787700246, 1, 0, 622600, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(52, 1, 877061698, 1, 0, 50500, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(59, 1, 5420647695, 2, 4112560, 5221560, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(60, 1, 5286684442, 1, 14800, 620300, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(63, 1, 5360262351, 2, 987345, 50722020, 1000000, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(64, 1, 1086894556, 1, 10600, 33600, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(65, 1, 603768385, 1, 0, 1801550, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(66, 1, 274092842, 1, 145600, 511600, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(67, 1, 1357307628, 1, 47950, 244050, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(68, 1, 263512715, 1, 513150, 1257150, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(70, 1, 442374124, 1, 190700, 2831450, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(72, 1, 5196684366, 1, 0, 176540, 100000, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(73, 1, 399258200, 2, 52600, 69100, 100000, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}'),
(74, 1, 6771784343, 1, 63450, 62950, 0, '{\"asiacell\":{},\"zain\":{},\"korek\":{},\"iraqsell\":{},\"alkafil\":{},\"creditrequest\":{},\"others\":{},\"netzain\":{},\"netasiacell\":{},\"total\":\"0\"}');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `bot`
--
ALTER TABLE `bot`
  ADD PRIMARY KEY (`key`);

--
-- Indexes for table `photos`
--
ALTER TABLE `photos`
  ADD PRIMARY KEY (`company`);

--
-- Indexes for table `priceslater`
--
ALTER TABLE `priceslater`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `pricesnow`
--
ALTER TABLE `pricesnow`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `request`
--
ALTER TABLE `request`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `states`
--
ALTER TABLE `states`
  ADD KEY `stateid_fk` (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD KEY `users_idx_from_id` (`from_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `request`
--
ALTER TABLE `request`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1313;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=75;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `states`
--
ALTER TABLE `states`
  ADD CONSTRAINT `stateid_fk` FOREIGN KEY (`id`) REFERENCES `users` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
