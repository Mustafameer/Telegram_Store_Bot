<?php

namespace TelegramBot\InlineKeyboardPagination\Tests;

use TelegramBot\InlineKeyboardPagination\InlineKeyboardPagination;

/**
 * Class InlineKeyboardPaginationTest
 */
final class InlineKeyboardPaginationTest extends \PHPUnit\Framework\TestCase
{
    /**
     * @var int
     */
    private $items_per_page = 5;

    /**
     * @var int
     */
    private $selected_page;

    /**
     * @var string
     */
    private $command;

    /**
     * @var array
     */
    private $items;

    /**
     * InlineKeyboardPaginationTest constructor.
     */
    public function __construct()
    {
        parent::__construct();

        $this->items         = range(1, 100);
        $this->command       = 'testCommand';
        $this->selected_page = random_int(1, 15);
    }

    public function testValidConstructor()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, $this->items_per_page);

        $data = $ikp->getPagination();

        $this->assertArrayHasKey('items', $data);
        $this->assertCount($this->items_per_page, $data['items']);
        $this->assertArrayHasKey('keyboard', $data);
        $this->assertArrayHasKey(0, $data['keyboard']);
        $this->assertArrayHasKey('text', $data['keyboard'][0]);
        $this->assertStringStartsWith("command={$this->command}", $data['keyboard'][0]['callback_data']);
    }

    /**
     * @expectedException \TelegramBot\InlineKeyboardPagination\Exceptions\InlineKeyboardPaginationException
     * @expectedExceptionMessage Invalid selected page, must be between 1 and 20
     */
    public function testInvalidConstructor()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, 10000, $this->items_per_page);
        $ikp->getPagination();
    }

    /**
     * @expectedException \TelegramBot\InlineKeyboardPagination\Exceptions\InlineKeyboardPaginationException
     * @expectedExceptionMessage Items list empty.
     */
    public function testEmptyItemsConstructor()
    {
        $ikp = new InlineKeyboardPagination([]);
        $ikp->getPagination();
    }

    public function testCallbackDataFormat()
    {
        $ikp = new InlineKeyboardPagination(range(1, 10), 'cmd', 2, 5);

        self::assertAllButtonPropertiesEqual([
            [
                'command=cmd&oldPage=2&newPage=1',
                'command=cmd&oldPage=2&newPage=2',
            ],
        ], 'callback_data', [$ikp->getPagination()['keyboard']]);

        $ikp->setCallbackDataFormat('{COMMAND};{OLD_PAGE};{NEW_PAGE}');

        self::assertAllButtonPropertiesEqual([
            [
                'cmd;2;1',
                'cmd;2;2',
            ],
        ], 'callback_data', [$ikp->getPagination()['keyboard']]);
    }

    public function testCallbackDataParser()
    {
        $ikp  = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, $this->items_per_page);
        $data = $ikp->getPagination();

        $callback_data = $ikp::getParametersFromCallbackData($data['keyboard'][0]['callback_data']);

        self::assertSame([
            'command' => $this->command,
            'oldPage' => "$this->selected_page",
            'newPage' => '1', // because we're getting the button at position 0, which is page 1
        ], $callback_data);
    }

    public function testValidPagination()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, $this->items_per_page);

        $length = (int) ceil(count($this->items) / $this->items_per_page);

        for ($i = 1; $i < $length; $i++) {
            $ikp->getPagination($i);
        }

        $this->assertTrue(true);
    }

    /**
     * @expectedException \TelegramBot\InlineKeyboardPagination\Exceptions\InlineKeyboardPaginationException
     * @expectedExceptionMessage Invalid selected page, must be between 1 and 20
     */
    public function testInvalidPagination()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, $this->items_per_page);
        $ikp->getPagination($ikp->getNumberOfPages() + 1);
    }

    public function testSetMaxButtons()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, $this->items_per_page);
        $ikp->setMaxButtons(6);
        self::assertTrue(true);
    }

    public function testForceButtonsCount()
    {
        $ikp = new InlineKeyboardPagination(range(1, 10), 'cbdata', 1, 1);

        // testing with 8 flexible buttons
        $ikp->setMaxButtons(8, false);

        self::assertAllButtonPropertiesEqual([
            ['· 1 ·', '2', '3', '4 ›', '5 ›', '6 ›', '7 ›', '10 »'],
        ], 'text', [$ikp->getPagination(1)['keyboard']]);

        self::assertAllButtonPropertiesEqual([
            ['« 1', '‹ 4', '· 5 ·', '6 ›', '10 »'],
        ], 'text', [$ikp->getPagination(5)['keyboard']]);

        // testing with 8 fixed buttons
        $ikp->setMaxButtons(8, true);

        self::assertAllButtonPropertiesEqual([
            ['· 1 ·', '2', '3', '4 ›', '5 ›', '6 ›', '7 ›', '10 »'],
        ], 'text', [$ikp->getPagination(1)['keyboard']]);

        self::assertAllButtonPropertiesEqual([
            ['· 1 ·', '2', '3', '4 ›', '5 ›', '6 ›', '7 ›', '10 »'],
        ], 'text', [$ikp->getPagination(1)['keyboard']]);

        self::assertAllButtonPropertiesEqual([
            ['« 1', '‹ 2', '‹ 3', '‹ 4', '· 5 ·', '6 ›', '7 ›', '10 »'],
        ], 'text', [$ikp->getPagination(5)['keyboard']]);

        // testing with 7 fixed buttons
        $ikp->setMaxButtons(7, true);

        self::assertAllButtonPropertiesEqual([
            ['· 1 ·', '2', '3', '4 ›', '5 ›', '6 ›', '10 »'],
        ], 'text', [$ikp->getPagination(1)['keyboard']]);

        self::assertAllButtonPropertiesEqual([
            ['« 1', '‹ 3', '‹ 4', '· 5 ·', '6 ›', '7 ›', '10 »'],
        ], 'text', [$ikp->getPagination(5)['keyboard']]);

        self::assertAllButtonPropertiesEqual([
            ['« 1', '‹ 5', '‹ 6', '‹ 7', '8', '9', '· 10 ·'],
        ], 'text', [$ikp->getPagination(10)['keyboard']]);
    }

    /**
     * @expectedException \TelegramBot\InlineKeyboardPagination\Exceptions\InlineKeyboardPaginationException
     * @expectedExceptionMessage Invalid max buttons, must be between 5 and 8.
     */
    public function testInvalidMaxButtons()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, $this->items_per_page);
        $ikp->setMaxButtons(2);
        $ikp->getPagination();
    }

    /**
     * @expectedException \TelegramBot\InlineKeyboardPagination\Exceptions\InlineKeyboardPaginationException
     * @expectedExceptionMessage Invalid selected page, must be between 1 and 20
     */
    public function testInvalidSelectedPage()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, $this->items_per_page);
        $ikp->setSelectedPage(-5);
        $ikp->getPagination();
    }

    public function testGetItemsPerPage()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, 4);
        self::assertEquals(4, $ikp->getItemsPerPage());
    }

    /**
     * @expectedException \TelegramBot\InlineKeyboardPagination\Exceptions\InlineKeyboardPaginationException
     * @expectedExceptionMessage Invalid number of items per page, must be at least 1
     */
    public function testInvalidItemsPerPage()
    {
        $ikp = new InlineKeyboardPagination($this->items, $this->command, $this->selected_page, 0);
        $ikp->getPagination();
    }

    public function testButtonLabels()
    {
        $cbdata  = 'command=%s&oldPage=%d&newPage=%d';
        $command = 'cbdata';
        $ikp1    = new InlineKeyboardPagination(range(1, 1), $command, 1, $this->items_per_page);
        $ikp10   = new InlineKeyboardPagination(range(1, $this->items_per_page * 10), $command, 1, $this->items_per_page);

        // current
        $keyboard = [$ikp1->getPagination(1)['keyboard']];
        self::assertAllButtonPropertiesEqual([
            ['· 1 ·'],
        ], 'text', $keyboard);
        self::assertAllButtonPropertiesEqual([
            [
                sprintf($cbdata, $command, 1, 1),
            ],
        ], 'callback_data', $keyboard);

        // first, previous, current, next, last
        $keyboard = [$ikp10->getPagination(5)['keyboard']];
        self::assertAllButtonPropertiesEqual([
            ['« 1', '‹ 4', '· 5 ·', '6 ›', '10 »'],
        ], 'text', $keyboard);
        self::assertAllButtonPropertiesEqual([
            [
                sprintf($cbdata, $command, 5, 1),
                sprintf($cbdata, $command, 5, 4),
                sprintf($cbdata, $command, 5, 5),
                sprintf($cbdata, $command, 5, 6),
                sprintf($cbdata, $command, 5, 10),
            ],
        ], 'callback_data', $keyboard);

        // first, previous, current, last
        $keyboard = [$ikp10->getPagination(9)['keyboard']];
        self::assertAllButtonPropertiesEqual([
            ['« 1', '‹ 7', '8', '· 9 ·', '10'],
        ], 'text', $keyboard);
        self::assertAllButtonPropertiesEqual([
            [
                sprintf($cbdata, $command, 9, 1),
                sprintf($cbdata, $command, 9, 7),
                sprintf($cbdata, $command, 9, 8),
                sprintf($cbdata, $command, 9, 9),
                sprintf($cbdata, $command, 9, 10),
            ],
        ], 'callback_data', $keyboard);

        // first, previous, current
        $keyboard = [$ikp10->getPagination(10)['keyboard']];
        self::assertAllButtonPropertiesEqual([
            ['« 1', '‹ 7', '8', '9', '· 10 ·'],
        ], 'text', $keyboard);
        self::assertAllButtonPropertiesEqual([
            [
                sprintf($cbdata, $command, 10, 1),
                sprintf($cbdata, $command, 10, 7),
                sprintf($cbdata, $command, 10, 8),
                sprintf($cbdata, $command, 10, 9),
                sprintf($cbdata, $command, 10, 10),
            ],
        ], 'callback_data', $keyboard);

        // custom labels, skipping some buttons
        // first, previous, current, next, last
        $labels = [
            'first'    => '',
            'previous' => 'previous %d',
            'current'  => null,
            'next'     => '%d next',
            'last'     => 'last',
        ];
        $ikp10->setLabels($labels);
        self::assertEquals($labels, $ikp10->getLabels());

        $keyboard = [$ikp10->getPagination(5)['keyboard']];
        self::assertAllButtonPropertiesEqual([
            ['previous 4', '6 next', 'last'],
        ], 'text', $keyboard);
        self::assertAllButtonPropertiesEqual([
            [
                sprintf($cbdata, $command, 5, 4),
                sprintf($cbdata, $command, 5, 6),
                sprintf($cbdata, $command, 5, 10),
            ],
        ], 'callback_data', $keyboard);
    }

    public static function assertButtonPropertiesEqual($value, $property, $keyboard, $row, $column, $message = '')
    {
        $row_raw    = array_values($keyboard)[$row];
        $column_raw = array_values($row_raw)[$column];

        self::assertSame($value, $column_raw[$property], $message);
    }

    public static function assertRowButtonPropertiesEqual(array $values, $property, $keyboard, $row, $message = '')
    {
        $column = 0;
        foreach ($values as $value) {
            self::assertButtonPropertiesEqual($value, $property, $keyboard, $row, $column++, $message);
        }
        self::assertCount(count(array_values($keyboard)[$row]), $values);
    }

    public static function assertAllButtonPropertiesEqual(array $all_values, $property, $keyboard, $message = '')
    {
        $row = 0;
        foreach ($all_values as $values) {
            self::assertRowButtonPropertiesEqual($values, $property, $keyboard, $row++, $message);
        }
        self::assertCount(count($keyboard), $all_values);
    }
}
